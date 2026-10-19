"""Conversation-level metrics with a fixed three-class label space."""

from collections import Counter
import math
import re

from .services import InputError
from .training_data import SCHEMA, PREPROCESSING, digest, fingerprint
from .services import validate_utterances


def validate_bundle(bundle):
    if not isinstance(bundle, dict) or bundle.get("schema_version") != SCHEMA or bundle.get("purpose") != "research_training_only":
        raise InputError("Không phải tập chia phục vụ nghiên cứu đã kiểm tra riêng tư.")
    if bundle.get("preprocessing_version") != PREPROCESSING:
        raise InputError("Phiên bản tiền xử lý không khớp.")
    if not isinstance(bundle.get("dataset_sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", bundle["dataset_sha256"]):
        raise InputError("Thiếu checksum bản xuất nguồn.")
    if bundle.get("bundle_sha256") != digest({k: v for k, v in bundle.items() if k != "bundle_sha256"}):
        raise InputError("Checksum tập chia không khớp.")
    if bundle.get("rubric_hash") != digest(bundle.get("rubric")):
        raise InputError("Checksum rubric không khớp.")
    report = bundle.get("report")
    if not isinstance(report, dict) or not isinstance(report.get("privacy_review"), dict):
        raise InputError("Thiếu ghi nhận kiểm tra riêng tư.")
    privacy = report["privacy_review"]
    if privacy.get("dataset_sha256") != bundle.get("dataset_sha256") or not isinstance(privacy.get("reviewer"), str) or not privacy["reviewer"].strip():
        raise InputError("Xác nhận riêng tư không khớp bản xuất.")
    if not isinstance(report.get("warnings"), list):
        raise InputError("Thiếu báo cáo chia tập.")
    rubric = bundle.get("rubric")
    if not isinstance(rubric, dict) or not isinstance(rubric.get("criteria"), list) or len(rubric["criteria"]) != 5 or any(not isinstance(c, dict) or not isinstance(c.get("code"), str) for c in rubric["criteria"]):
        raise InputError("Cấu trúc rubric không hợp lệ.")
    weights = [c.get("weight") for c in rubric["criteria"]]
    if len({c["code"] for c in rubric["criteria"]}) != 5 or any(type(w) not in (int, float) or not math.isfinite(w) or not 0 < w <= 1 for w in weights) or not math.isclose(sum(weights), 1):
        raise InputError("Mã tiêu chí hoặc trọng số rubric không hợp lệ.")
    splits = bundle.get("splits")
    if not isinstance(splits, dict) or set(splits) != {"train", "validation", "test"} or any(not isinstance(x, list) or not x for x in splits.values()):
        raise InputError("Cần ba tập train/validation/test không rỗng.")
    seen = {}
    codes = [c["code"] for c in bundle["rubric"]["criteria"]]
    for name, rows in splits.items():
        for row in rows:
            if not isinstance(row, dict) or any(not isinstance(row.get(f), str) or not row[f] for f in ("conversation_id", "group_id", "content_hash")):
                raise InputError("Bản ghi tập chia không hợp lệ.")
            if not isinstance(row.get("labels"), dict) or set(row["labels"]) != set(codes) or any(v is not None and (type(v) is not int or v not in (0, 1, 2)) for v in row["labels"].values()):
                raise InputError("Nhãn trong tập chia không hợp lệ.")
            turns = validate_utterances(row.get("utterances"))
            if any(t["role"] == "unknown" for t in turns) or fingerprint(turns) != row["content_hash"]:
                raise InputError("Nội dung đã thay đổi sau khi chia tập.")
            for field in ("conversation_id", "group_id", "content_hash"):
                key = (field, row[field])
                if key in seen and (field == "conversation_id" or seen[key] != name):
                    raise InputError("Trùng cuộc gọi hoặc rò rỉ nhóm/nội dung giữa các tập.")
                seen[key] = name
    return splits


def majority_baseline(train, codes):
    predictions = {}
    for code in codes:
        counts = Counter(row["labels"][code] for row in train if row["labels"][code] is not None)
        if not counts:
            raise InputError(f"Tập train không có nhãn quan sát được cho {code}.")
        label = min(counts, key=lambda i: (-counts[i], i))
        predictions[code] = {"score": label, "class_frequencies": [counts[i] / sum(counts.values()) for i in range(3)]}
    return predictions


def evaluate(rows, predictions, rubric):
    if len(rows) != len(predictions):
        raise InputError("Số dự đoán không khớp số hội thoại.")
    report = {"criteria": {}, "conversation_count": len(rows), "review_required_rate": 1.0 if rows else None,
        "evidence_verified": False, "total_mae": None, "total_eligible_count": 0,
        "confidence_note": "Xác suất chưa được hiệu chỉnh; mọi kết quả vẫn cần người duyệt."}
    total_errors = []
    for c in rubric["criteria"]:
        code = c["code"]
        matrix = [[0] * 3 for _ in range(3)]
        absolute = []
        for row, pred in zip(rows, predictions):
            truth = row["labels"][code]
            value = pred.get(code)
            if type(value) is not int or value not in (0, 1, 2):
                raise InputError("Dự đoán phải là int 0/1/2.")
            if truth is not None:
                matrix[truth][value] += 1
                absolute.append(abs(truth - value))
        f1 = []
        for i in range(3):
            tp = matrix[i][i]
            denominator = sum(matrix[i]) + sum(row[i] for row in matrix)
            f1.append(2 * tp / denominator if denominator else 0.0)
        report["criteria"][code] = {"macro_f1": sum(f1) / 3 if absolute else None,
            "confusion_matrix": matrix, "labels": [0, 1, 2], "support": [sum(row) for row in matrix],
            "observed_count": len(absolute), "masked_count": len(rows) - len(absolute),
            "mae": sum(absolute) / len(absolute) if absolute else None}
    for row, pred in zip(rows, predictions):
        if all(row["labels"][c["code"]] is not None for c in rubric["criteria"]):
            true_total = sum(row["labels"][c["code"]] * c["weight"] * 50 for c in rubric["criteria"])
            predicted_total = sum(pred[c["code"]] * c["weight"] * 50 for c in rubric["criteria"])
            total_errors.append(abs(true_total - predicted_total))
    report["total_eligible_count"] = len(total_errors)
    report["total_mae"] = sum(total_errors) / len(total_errors) if total_errors else None
    return report
