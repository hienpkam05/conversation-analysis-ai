"""Local, manifest-pinned inference. Importing this module never loads ML libraries."""

import hashlib
import importlib.util
import json
import math
from pathlib import Path
from django.utils.dateparse import parse_datetime

from django.conf import settings

from .services import InputError, validate_ratings, validate_utterances
from .training_data import definitions, digest

FORMAT = "quality-videberta-five-head-v1"
PREPROCESSING = "role-prefix-token-windows-mean-prob-v1"
ERRORS = {
    "QUALITY_MODEL_UNAVAILABLE": "Chưa cấu hình checkpoint chất lượng tư vấn đã train và duyệt.",
    "MODEL_MANIFEST_INVALID": "Cấu hình checkpoint không hợp lệ hoặc file model chưa đầy đủ.",
    "MODEL_NOT_APPROVED": "Checkpoint chưa được duyệt sử dụng sau đánh giá độc lập.",
    "MODEL_DEPENDENCIES_MISSING": "Môi trường worker thiếu torch, transformers hoặc safetensors.",
    "RUBRIC_MODEL_MISMATCH": "Checkpoint không tương thích với phiên bản tiêu chí đang chọn.",
    "MODEL_CHANGED": "Checkpoint đã thay đổi sau khi gửi yêu cầu. Gửi yêu cầu mới sau khi kiểm tra.",
    "MODEL_LOAD_FAILED": "Không mở được checkpoint. Kiểm tra log vận hành và cấu hình model local.",
    "MODEL_INFERENCE_FAILED": "Worker không thể hoàn tất suy luận. Chưa có điểm AI nào được lưu.",
    "MODEL_OUTPUT_INVALID": "Đầu ra model không hợp lệ; hệ thống không lưu điểm hoặc dẫn chứng sai.",
    "JOB_TIMEOUT": "Tác vụ vượt thời gian xử lý cho phép. Không tự chạy lại.",
    "WORKER_INTERRUPTED": "Worker bị ngắt trước khi hoàn tất. Không tự chạy lại.",
    "INPUT_TOO_LARGE": "Hội thoại vượt số cửa sổ model cho phép; không cắt bỏ âm thầm phần cuối.",
    "REVISION_CHANGED": "Nội dung hoặc xác nhận hội thoại đã thay đổi; hãy kiểm tra lại.",
    "ACCESS_REVOKED": "Tài khoản gửi yêu cầu không còn quyền truy cập hội thoại.",
    "RUBRIC_NOT_APPROVED": "Bộ tiêu chí chưa được duyệt hoặc đã ngừng sử dụng.",
}


class InferenceError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(ERRORS.get(code, ERRORS["MODEL_INFERENCE_FAILED"]))


def read_spec():
    root = getattr(settings, "QUALITY_MODEL_DIR", "")
    if not root:
        raise InferenceError("QUALITY_MODEL_UNAVAILABLE")
    try:
        root = Path(root).resolve(strict=True)
        manifest = root / "quality-manifest.json"
        if not manifest.is_file() or manifest.stat().st_size > 65536:
            raise ValueError()
        spec = json.loads(manifest.read_text(encoding="utf-8"))
        if not isinstance(spec, dict) or spec.get("format") != FORMAT or spec.get("preprocessing_version") != PREPROCESSING:
            raise ValueError()
        for field in ("model_version", "rubric_version", "rubric_hash", "approved_by", "approved_at", "evaluation_sha256"):
            if not isinstance(spec.get(field), str) or not spec[field].strip() or len(spec[field]) > 200:
                raise ValueError()
        if spec.get("approved_for_use") is not True:
            raise InferenceError("MODEL_NOT_APPROVED")
        for field in ("rubric_hash", "evaluation_sha256"):
            if len(spec[field]) != 64 or any(c not in "0123456789abcdef" for c in spec[field]):
                raise ValueError()
        if parse_datetime(spec["approved_at"]) is None:
            raise ValueError()
        codes = spec.get("criteria")
        thresholds = spec.get("confidence_thresholds")
        if (not isinstance(codes, list) or len(codes) != 5 or any(not isinstance(c, str) for c in codes) or len(set(codes)) != 5
                or not isinstance(thresholds, dict) or set(thresholds) != set(codes)):
            raise ValueError()
        if any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in thresholds.values()):
            raise ValueError()
        length, overlap, limit = spec.get("max_length"), spec.get("overlap_tokens"), spec.get("max_windows")
        if (type(length) is not int or not 16 <= length <= 512 or type(overlap) is not int or not 0 <= overlap < length - 4
                or type(limit) is not int or not 1 <= limit <= 256):
            raise ValueError()
        files = spec.get("files")
        if not isinstance(files, dict) or not {"config.json", "tokenizer.json", "quality.safetensors"} <= set(files):
            raise ValueError()
        for name, checksum in files.items():
            path = root / name
            if (not isinstance(name, str) or Path(name).name != name or path.resolve().parent != root or
                    not path.is_file() or not isinstance(checksum, str) or len(checksum) != 64 or
                    any(c not in "0123456789abcdef" for c in checksum)):
                raise ValueError()
        if (root / "config.json").stat().st_size > 65536:
            raise ValueError()
        config = json.loads((root / "config.json").read_text(encoding="utf-8"))
        if config.get("model_type") != "deberta-v2" or type(config.get("hidden_size")) is not int or not 1 <= config["hidden_size"] <= 4096:
            raise ValueError()
        if length > config.get("max_position_embeddings", 0):
            raise ValueError()
        return root, spec, digest(spec)
    except InferenceError:
        raise
    except (OSError, ValueError, TypeError, AttributeError):
        raise InferenceError("MODEL_MANIFEST_INVALID") from None


def check_compatibility(spec, rubric):
    if (spec["rubric_version"] != rubric.version or spec["rubric_hash"] != digest(definitions(rubric.criteria_json))
            or set(spec["criteria"]) != {c["code"] for c in rubric.criteria_json["criteria"]}):
        raise InferenceError("RUBRIC_MODEL_MISMATCH")


def status():
    try:
        _, spec, _ = read_spec()
        if any(importlib.util.find_spec(m) is None for m in ("torch", "transformers", "safetensors")):
            raise InferenceError("MODEL_DEPENDENCIES_MISSING")
        return {"available": True, "code": None, "message": "Checkpoint đã cấu hình; kết quả AI luôn cần người duyệt.",
            "model_version": spec["model_version"], "rubric_version": spec["rubric_version"],
            "preprocessing_version": spec["preprocessing_version"], "requires_human_review": True}
    except InferenceError as exc:
        return {"available": False, "code": exc.code, "message": str(exc), "requires_human_review": True}


def token_windows(ids, capacity, overlap, limit):
    if not ids or capacity <= 0 or not 0 <= overlap < capacity:
        raise InferenceError("MODEL_OUTPUT_INVALID")
    windows = []
    for start in range(0, len(ids), capacity - overlap):
        windows.append(ids[start:start + capacity])
        if len(windows) > limit:
            raise InferenceError("INPUT_TOO_LARGE")
        if start + capacity >= len(ids):
            break
    return windows


def normalize_output(result, spec, utterances, rubric):
    if not isinstance(result, dict) or set(result) != {"probabilities", "windows"}:
        raise InferenceError("MODEL_OUTPUT_INVALID")
    probabilities = result["probabilities"]
    if not isinstance(probabilities, dict) or set(probabilities) != set(spec["criteria"]) or type(result["windows"]) is not int or not 1 <= result["windows"] <= spec["max_windows"]:
        raise InferenceError("MODEL_OUTPUT_INVALID")
    ratings, confidence = [], {}
    for code in spec["criteria"]:
        probs = probabilities[code]
        if (not isinstance(probs, list) or len(probs) != 3 or any(type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1 for p in probs)
                or not math.isclose(sum(probs), 1, abs_tol=1e-5)):
            raise InferenceError("MODEL_OUTPUT_INVALID")
        score = max(range(3), key=lambda i: probs[i])
        confidence[code] = probs[score]
        low = probs[score] < spec["confidence_thresholds"][code]
        ratings.append({"criterion_code": code, "score": None if low else score,
            "not_assessable_reason": "Model chưa đạt ngưỡng đã cấu hình; cần người kiểm tra." if low else "",
            "comment": "", "evidence": {"kind": "quote", "utterance_ids": []}})
    try:
        clean, _ = validate_ratings(ratings, utterances, allow_incomplete=True, rubric=rubric)
    except InputError:
        raise InferenceError("MODEL_OUTPUT_INVALID") from None
    return clean, {"probabilities": probabilities, "confidence": confidence, "windows": result["windows"],
        "evidence_verified": False, "review_required": True, "confidence_calibrated": False}


class LocalProvider:
    def __init__(self, root, spec):
        self.root, self.spec = root, spec

    def predict(self, turns, progress):
        turns = validate_utterances(turns)
        try:
            import torch
            from torch import nn
            from safetensors.torch import load_file
            from transformers import AutoConfig, AutoModel, AutoTokenizer
        except ImportError:
            raise InferenceError("MODEL_DEPENDENCIES_MISSING") from None
        try:
            for name, expected in self.spec["files"].items():
                with (self.root / name).open("rb") as stream:
                    checksum = hashlib.file_digest(stream, "sha256").hexdigest()
                if checksum != expected:
                    raise InferenceError("MODEL_CHANGED")

            class FiveHead(nn.Module):
                def __init__(inner):
                    super().__init__()
                    config = AutoConfig.from_pretrained(str(self.root), local_files_only=True, trust_remote_code=False)
                    inner.encoder = AutoModel.from_config(config, trust_remote_code=False)
                    inner.heads = nn.ModuleDict({c: nn.Linear(config.hidden_size, 3) for c in self.spec["criteria"]})

                def forward(inner, **inputs):
                    cls = inner.encoder(**inputs).last_hidden_state[:, 0]
                    return {c: head(cls) for c, head in inner.heads.items()}

            model = FiveHead()
            model.load_state_dict(load_file(str(self.root / "quality.safetensors")), strict=True)
            model.eval()
            tokenizer = AutoTokenizer.from_pretrained(str(self.root), local_files_only=True, trust_remote_code=False, use_fast=True)
            special = tokenizer.num_special_tokens_to_add(pair=False)
            capacity = self.spec["max_length"] - special
            if not 0 <= self.spec["overlap_tokens"] < capacity:
                raise ValueError()
        except InferenceError:
            raise
        except Exception:
            raise InferenceError("MODEL_LOAD_FAILED") from None
        text = "\n".join(f"{'Tư vấn viên' if t['role'] == 'consultant' else 'Ứng viên'}: {t['text']}" for t in turns)
        ids = tokenizer.encode(text, add_special_tokens=False, truncation=False)
        windows = token_windows(ids, capacity, self.spec["overlap_tokens"], self.spec["max_windows"])
        totals = {c: [0.0, 0.0, 0.0] for c in self.spec["criteria"]}
        progress(0, len(windows))
        with torch.inference_mode():
            for index, window in enumerate(windows, 1):
                inputs = tokenizer.prepare_for_model(window, add_special_tokens=True, return_tensors="pt", return_attention_mask=True, truncation=False)
                output = model(**inputs)
                for code, logits in output.items():
                    values = torch.softmax(logits.float(), dim=-1)[0].tolist()
                    totals[code] = [a + b for a, b in zip(totals[code], values)]
                progress(index, len(windows))
        return {"probabilities": {c: [p / len(windows) for p in values] for c, values in totals.items()}, "windows": len(windows)}
