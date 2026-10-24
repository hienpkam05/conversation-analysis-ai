"""Shared preprocessing for offline training and local inference; no ML imports at startup."""
import hashlib
import json

from consultation_quality.services import InputError, validate_utterances
from consultation_quality.training_data import redact
from .metrics import CODES

FORMAT = "candidate-status-videberta-v1"
WINDOWING = "status-role-windows-mean-prob-v1"


def text_for(turns):
    names = {"candidate": "Ứng viên", "consultant": "Tư vấn viên", "unknown": "Chưa rõ"}
    return "\n".join(f"{names[t['role']]}: {redact(t['text'])}" for t in validate_utterances(turns) if not t.get("unclear"))


def windows_for(tokenizer, turns, max_length=256, max_windows=16):
    ids = tokenizer.encode(text_for(turns), add_special_tokens=False, truncation=False)
    capacity = max_length - tokenizer.num_special_tokens_to_add(pair=False)
    if not ids or capacity < 8:
        raise InputError("Không có văn bản nghe rõ đủ để suy luận.")
    windows = [ids[i:i + capacity] for i in range(0, len(ids), capacity)]
    if len(windows) > max_windows:
        raise InputError("Hội thoại vượt giới hạn cửa sổ model; không cắt bỏ phần cuối.", "INPUT_TOO_LARGE")
    return windows


def forward_probabilities(torch, model, tokenizer, turns, device, max_length, max_windows):
    probabilities = []
    for window in windows_for(tokenizer, turns, max_length, max_windows):
        values = tokenizer.prepare_for_model(window, add_special_tokens=True, return_attention_mask=True)
        inputs = {key: torch.tensor([value], device=device) for key, value in values.items() if key in ("input_ids", "attention_mask", "token_type_ids")}
        probabilities.append(torch.softmax(model(**inputs).logits.float()[0], dim=-1))
    return torch.stack(probabilities).mean(dim=0)


def file_hash(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)


def labels_config():
    return {"id2label": {i: code for i, code in enumerate(CODES)}, "label2id": {code: i for i, code in enumerate(CODES)}}
