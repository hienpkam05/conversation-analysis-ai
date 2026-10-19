import math
import uuid

from .rubric import RUBRIC


class InputError(ValueError):
    def __init__(self, message, code="INVALID_INPUT"):
        super().__init__(message)
        self.code = code


def transcript_review_flags(utterances, raw_segments):
    """Surface ASR suspicions for listening; do not delete or relabel speech."""
    raw_by_id = {x.get("id"): x for x in raw_segments if isinstance(x, dict)}
    flags = []
    for turn in utterances:
        text = turn["text"].casefold()
        reasons = []
        if any(phrase in text for phrase in ("subscribe", "lalaschool", "ghiền mì gõ", "đăng ký kênh", "đăng kí kênh")):
            reasons.append("Có cụm từ dễ bị nhận dạng nhầm; cần nghe đối chiếu.")
        words = text.split()
        if len(words) >= 12 and len(set(words)) / len(words) < 0.25:
            reasons.append("Nội dung lặp nhiều; cần kiểm tra với audio.")
        raw = raw_by_id.get(turn["id"], {})
        if raw.get("text") == turn["text"] and raw.get("avg_logprob", 0) < -1:
            reasons.append("Độ chắc chắn nhận dạng thấp; cần nghe lại.")
        if reasons:
            flags.append({"utterance_id": turn["id"], "reasons": reasons})
    return flags


def validate_utterances(raw):
    if not isinstance(raw, list) or not 1 <= len(raw) <= 5000:
        raise InputError("Cần từ 1 đến 5.000 lượt nói.")
    result, seen = [], set()
    for position, item in enumerate(raw, 1):
        if not isinstance(item, dict):
            raise InputError("Lượt nói không hợp lệ.")
        text = item.get("text", "")
        role = item.get("role", "unknown")
        key = str(item.get("id") or uuid.uuid4())
        if key in seen or len(key) > 64:
            raise InputError("ID lượt nói bị trùng hoặc không hợp lệ.")
        seen.add(key)
        if not isinstance(text, str) or not text.strip() or len(text) > 10000:
            raise InputError("Mỗi lượt cần nội dung từ 1 đến 10.000 ký tự.")
        if not isinstance(role, str) or role not in {"consultant", "candidate", "unknown"}:
            raise InputError("Vai trò người nói không hợp lệ.")
        start, end = item.get("start_seconds"), item.get("end_seconds")
        if start is not None or end is not None:
            if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in (start, end)) or not 0 <= start < end:
                raise InputError("Thời gian lượt nói không hợp lệ.")
        unclear = item.get("unclear", False)
        if type(unclear) is not bool:
            raise InputError("Cờ khó nghe không hợp lệ.")
        result.append({"id": key, "position": position, "role": role, "text": text.strip(), "start_seconds": start, "end_seconds": end, **({"unclear": True} if unclear else {})})
    if sum(len(x["text"]) for x in result) > 200000:
        raise InputError("Hội thoại vượt 200.000 ký tự.", "INPUT_TOO_LARGE")
    return result


def validate_ratings(raw, utterances, allow_incomplete=False, rubric=None):
    rubric = rubric or RUBRIC
    codes = {c["code"] for c in rubric["criteria"]}
    if not isinstance(raw, list) or len(raw) != 5 or any(not isinstance(x, dict) for x in raw):
        raise InputError("Cần chấm đủ 5 tiêu chí.")
    if any(not isinstance(x.get("criterion_code"), str) for x in raw) or {x.get("criterion_code") for x in raw} != codes:
        raise InputError("Mã tiêu chí thiếu hoặc bị trùng.")
    turns = {x["id"]: x for x in utterances}
    clean = []
    complete = True
    for item in raw:
        score = item.get("score")
        reason, comment = item.get("not_assessable_reason", ""), item.get("comment", "")
        if any(not isinstance(x, str) or len(x) > 5000 for x in (reason, comment)):
            raise InputError("Nhận xét không hợp lệ.")
        if score is not None and (type(score) is not int or score not in (0, 1, 2)):
            raise InputError("Điểm phải là 0, 1, 2 hoặc không đủ dữ liệu.")
        evidence = item.get("evidence", {})
        if not isinstance(evidence, dict):
            raise InputError("Dẫn chứng không hợp lệ.", "INVALID_EVIDENCE")
        ids, kind = evidence.get("utterance_ids", []), evidence.get("kind", "quote")
        explanation = evidence.get("explanation", "")
        if not isinstance(kind, str) or kind not in {"quote", "absence"} or not isinstance(explanation, str) or len(explanation) > 5000:
            raise InputError("Loại hoặc giải thích dẫn chứng không hợp lệ.", "INVALID_EVIDENCE")
        if not isinstance(ids, list) or any(not isinstance(i, str) or i not in turns for i in ids):
            raise InputError("Dẫn chứng phải thuộc hội thoại này.", "INVALID_EVIDENCE")
        if score is None:
            complete = False
            if not reason.strip() and not allow_incomplete:
                raise InputError("Hãy ghi lý do không đủ dữ liệu.")
        else:
            if (not ids and not allow_incomplete) or not isinstance(kind, str) or kind not in {"quote", "absence"}:
                raise InputError("Hãy chọn lời thoại hoặc phạm vi đã xem xét.", "INVALID_EVIDENCE")
            if kind == "absence" and (score != 0 or not (comment.strip() or explanation.strip()) and not allow_incomplete):
                raise InputError("Không xuất hiện hành vi cần điểm 0 và lời giải thích.", "INVALID_EVIDENCE")
            if kind == "quote" and not allow_incomplete and not any(turns[i]["role"] == "consultant" for i in ids):
                raise InputError("Dẫn chứng cần có lời của tư vấn viên.", "INVALID_EVIDENCE")
            if not ids or kind == "absence" and not (comment.strip() or explanation.strip()) or kind == "quote" and not any(turns[i]["role"] == "consultant" for i in ids):
                complete = False
        clean.append({"criterion_code": item["criterion_code"], "score": score, "not_assessable_reason": reason.strip(), "comment": comment.strip(), "evidence": {"kind": kind, "utterance_ids": list(dict.fromkeys(ids)), "explanation": explanation.strip()}})
    weights = {c["code"]: c["weight"] for c in rubric["criteria"]}
    total = round(sum(x["score"] / 2 * weights[x["criterion_code"]] * 100 for x in clean), 6) if complete else None
    return clean, total
