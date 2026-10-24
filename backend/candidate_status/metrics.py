import math

from consultation_quality.services import InputError
from .services import LABEL_MAP

CODES = list(LABEL_MAP)


def probability_label(probs, threshold):
    if not isinstance(probs, list) or len(probs) != len(CODES) or any(type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1 for p in probs) or not math.isclose(sum(probs), 1, abs_tol=1e-5):
        raise InputError("Xác suất model không hợp lệ.")
    if type(threshold) not in (int, float) or not math.isfinite(threshold) or not 0 <= threshold <= 1:
        raise InputError("Ngưỡng model không hợp lệ.")
    index = max(range(len(probs)), key=lambda i: probs[i])
    return CODES[index] if probs[index] >= threshold else "unknown"


def scores(truth, predicted):
    if not truth or len(truth) != len(predicted) or any(x not in CODES for x in truth + predicted):
        raise InputError("Cần nhãn thật/dự đoán hợp lệ cùng kích thước.")
    matrix = [[0] * len(CODES) for _ in CODES]
    for actual, pred in zip(truth, predicted):
        matrix[CODES.index(actual)][CODES.index(pred)] += 1
    per_class = {}
    for i, code in enumerate(CODES):
        tp = matrix[i][i]
        support = sum(matrix[i])
        predicted_count = sum(row[i] for row in matrix)
        precision, recall = tp / predicted_count if predicted_count else 0, tp / support if support else 0
        per_class[code] = {"precision": precision, "recall": recall, "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0, "support": support}
    return {"labels": CODES, "macro_f1": sum(row["f1"] for row in per_class.values()) / len(CODES),
        "accuracy": sum(a == b for a, b in zip(truth, predicted)) / len(truth), "per_class": per_class, "confusion_matrix": matrix,
        "unknown_rate": predicted.count("unknown") / len(predicted), "count": len(truth)}


def select_threshold(truth, probabilities):
    if len(truth) != len(probabilities) or not truth:
        raise InputError("Thiếu validation để chọn ngưỡng.")
    trials = []
    for threshold in (0.0, .4, .5, .6, .7, .8, .9):
        report = scores(truth, [probability_label(row, threshold) for row in probabilities])
        trials.append((report["macro_f1"], -report["unknown_rate"], -threshold, threshold))
    return max(trials)[-1]
