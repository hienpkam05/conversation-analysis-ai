import importlib.util
import json
import math
from pathlib import Path
import threading

from django.conf import settings
from django.utils.dateparse import parse_datetime

from consultation_quality.services import InputError
from consultation_quality.training_data import digest
from .metrics import CODES, probability_label
from .ml import FORMAT, WINDOWING, file_hash, forward_probabilities
from .review import approval, definitions

_lock = threading.Lock()


def read_manifest(require_approved=True):
    configured = getattr(settings, "STATUS_MODEL_DIR", "")
    if not configured:
        raise InputError("Chưa cấu hình checkpoint trạng thái đã huấn luyện và duyệt.", "STATUS_MODEL_UNAVAILABLE")
    try:
        root = Path(configured).resolve(strict=True)
        path = root / "status-manifest.json"
        if path.stat().st_size > 65536:
            raise ValueError()
        spec = json.loads(path.read_text(encoding="utf-8"))
        if spec.get("format") != FORMAT or spec.get("preprocessing") != WINDOWING or spec.get("labels") != CODES or spec.get("definition_hash") != digest(definitions()):
            raise ValueError()
        if not isinstance(spec.get("model_version"), str) or not spec["model_version"].strip() or len(spec["model_version"]) > 200:
            raise ValueError()
        if not approval():
            raise InputError("Bộ nhãn trạng thái chưa được duyệt.")
        if require_approved and (spec.get("approved_for_use") is not True or not spec.get("approved_by") or not spec.get("approved_at")):
            raise InputError("Checkpoint chưa được người phụ trách duyệt sử dụng.", "STATUS_MODEL_UNAPPROVED")
        length, limit, threshold = spec.get("max_length"), spec.get("max_windows"), spec.get("threshold")
        if type(length) is not int or not 32 <= length <= 512 or type(limit) is not int or not 1 <= limit <= 32 or type(threshold) not in (float, int) or not math.isfinite(threshold) or not 0 <= threshold <= 1:
            raise ValueError()
        files = spec.get("files")
        if not isinstance(files, dict) or not {"config.json", "tokenizer.json", "tokenizer_config.json", "model.safetensors", "evaluation.json"} <= set(files):
            raise ValueError()
        for name, checksum in files.items():
            path = root / name
            if Path(name).name != name or path.resolve().parent != root or not path.is_file() or not isinstance(checksum, str) or len(checksum) != 64 or any(c not in "0123456789abcdef" for c in checksum):
                raise ValueError()
        if require_approved:
            stamp = parse_datetime(spec["approved_at"]) if isinstance(spec.get("approved_at"), str) else None
            if (stamp is None or stamp.tzinfo is None or not isinstance(spec.get("approved_by"), str)
                    or not spec["approved_by"].strip() or spec.get("license_reviewed_for_release") is not True
                    or spec.get("evaluation_review_sha256") != files["evaluation.json"]):
                raise ValueError()
        if any(path.name not in files for path in root.iterdir() if path.is_file() and path.name != "status-manifest.json"):
            raise ValueError()
        return root, spec
    except InputError:
        raise
    except (OSError, ValueError, TypeError, AttributeError):
        raise InputError("Manifest checkpoint không hợp lệ.", "STATUS_MANIFEST_INVALID") from None


def model_status():
    try:
        _, spec = read_manifest()
        if any(importlib.util.find_spec(name) is None for name in ("torch", "transformers", "safetensors")):
            raise InputError("Môi trường web thiếu thư viện suy luận; xem TRAINING.md.", "STATUS_DEPENDENCIES_MISSING")
        return {"available": True, "code": None, "model_version": spec["model_version"], "message": "Checkpoint đã cấu hình; dự đoán luôn cần người đối chiếu."}
    except InputError as exc:
        return {"available": False, "code": exc.code, "message": str(exc), "model_version": None}


def predict(turns):
    if not _lock.acquire(blocking=False):
        raise InputError("Model đang xử lý một hội thoại khác. Thử lại sau.", "QUEUE_FULL")
    try:
        root, spec = read_manifest()
        if any(file_hash(root / name) != expected for name, expected in spec["files"].items()):
            raise InputError("Checkpoint đã đổi sau khi duyệt; không suy luận.", "STATUS_MODEL_CHANGED")
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError:
            raise InputError("Thiếu thư viện suy luận.", "STATUS_DEPENDENCIES_MISSING") from None
        try:
            tokenizer = AutoTokenizer.from_pretrained(str(root), local_files_only=True, trust_remote_code=False, use_fast=True)
            model = AutoModelForSequenceClassification.from_pretrained(str(root), local_files_only=True, trust_remote_code=False, use_safetensors=True)
            if model.config.model_type != "deberta-v2" or model.config.id2label != {i: code for i, code in enumerate(CODES)} or spec["max_length"] > model.config.max_position_embeddings:
                raise InputError("Cấu hình model không khớp bộ nhãn đã duyệt.")
            model.eval()
            with torch.inference_mode():
                probs = forward_probabilities(torch, model, tokenizer, turns, "cpu", spec["max_length"], spec["max_windows"]).tolist()
            label = probability_label(probs, spec["threshold"])
        except InputError:
            raise
        except Exception:
            raise InputError("Không mở/chạy được model local; chưa lưu dự đoán.", "STATUS_INFERENCE_FAILED") from None
        return {"label": label, "evidence_ids": [], "rationale": "Dự đoán ViDeBERTa chưa có dẫn chứng được kiểm chứng; cần tạo bản thủ công và đối chiếu.",
            "metadata": {"method": "videberta", "probabilities": dict(zip(CODES, probs)), "confidence": max(probs),
                "raw_label": CODES[max(range(len(probs)), key=lambda i: probs[i])],
                "abstained": max(probs) < spec["threshold"],
                "confidence_calibrated": False, "model_version": spec["model_version"], "manifest_sha256": digest(spec), "review_required": True}}
    except OSError:
        raise InputError("Không đọc được file checkpoint local; chưa lưu dự đoán.", "STATUS_MODEL_UNAVAILABLE") from None
    finally:
        _lock.release()
