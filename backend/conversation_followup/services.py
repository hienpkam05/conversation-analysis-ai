import unicodedata
from datetime import timedelta
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from consultation_quality.services import InputError, validate_utterances

CATEGORIES = {"context": "Ngữ cảnh", "needs": "Nhu cầu ứng viên", "job": "Thông tin công việc", "questions": "Câu hỏi cần đối chiếu", "next_steps": "Lời nhắc về bước tiếp theo"}


def normalize(text):
    return unicodedata.normalize("NFC", text).casefold()


def extract(utterances):
    turns = validate_utterances(utterances)
    buckets = {code: [] for code in CATEGORIES}
    for t in turns:
        text = normalize(t["text"])
        item = {"text": t["text"], "utterance_ids": [t["id"]]}
        if t["role"] == "candidate" and any(w in text for w in ("muốn", "mong", "cần", "ca ngày", "ca đêm", "gần nhà")):
            buckets["needs"].append(item)
        if t["role"] == "consultant" and any(w in text for w in ("lương", "công việc", "vị trí", "tăng ca", "nơi làm", "ký túc", "phụ cấp")):
            buckets["job"].append(item)
        if "?" in t["text"]:
            buckets["questions"].append(item)
        if any(w in text for w in ("hẹn", "phỏng vấn", "gọi lại", "liên hệ lại", "gửi", "zalo", "ngày mai", "tuần sau")):
            buckets["next_steps"].append(item)
    buckets["context"] = [{"text": t["text"], "utterance_ids": [t["id"]]} for t in ([turns[0]] if len(turns) == 1 else [turns[0], turns[-1]])]
    sections, omitted, characters = [], {}, 0
    for code, items in buckets.items():
        omitted[code] = max(0, len(items) - 3)
        if len(items) > 3:
            items = [items[0], items[len(items) // 2], items[-1]]
        bounded = []
        for item in items:
            if characters + len(item["text"]) <= 100000:
                bounded.append(item)
                characters += len(item["text"])
            else:
                omitted[code] += 1
        items = bounded
        sections.append({"code": code, "items": items})
    return sections, {"method": "extractive-keywords-v1", "omitted_matches": omitted, "automatic_appointment": False,
        "notice": "Các câu trích không xác nhận ý định hay việc hai bên đã thống nhất lịch."}


def validate_sections(value, turns):
    ids = {t["id"] for t in turns}
    if not isinstance(value, list) or len(value) != len(CATEGORIES) or any(not isinstance(s, dict) for s in value):
        raise InputError("Cần đủ năm mục tóm tắt.")
    if any(not isinstance(s.get("code"), str) for s in value) or {s["code"] for s in value} != set(CATEGORIES):
        raise InputError("Mục tóm tắt thiếu hoặc trùng mã.")
    clean = []
    for section in value:
        items = section.get("items")
        if not isinstance(items, list) or len(items) > 20:
            raise InputError("Mỗi mục tối đa 20 ý.")
        rows = []
        for item in items:
            if not isinstance(item, dict):
                raise InputError("Ý tóm tắt không hợp lệ.")
            text, evidence = item.get("text"), item.get("utterance_ids")
            if not isinstance(text, str) or not text.strip() or len(text) > 10000:
                raise InputError("Nội dung mỗi ý cần từ 1 đến 10.000 ký tự.")
            if not isinstance(evidence, list) or not evidence or any(not isinstance(i, str) or i not in ids for i in evidence):
                raise InputError("Mỗi ý cần dẫn chứng thuộc đúng phiên bản hội thoại.", "INVALID_EVIDENCE")
            rows.append({"text": text.strip(), "utterance_ids": list(dict.fromkeys(evidence))})
        clean.append({"code": section["code"], "items": rows})
    if not any(s["items"] for s in clean) or sum(len(i["text"]) for s in clean for i in s["items"]) > 100000:
        raise InputError("Tóm tắt rỗng hoặc vượt 100.000 ký tự.")
    return clean


def check_current(summary):
    revision = summary.revision
    latest = revision.conversation.revisions.order_by("-revision_number").first()
    if latest.pk != revision.pk or revision.content_hash != summary.revision_hash or revision.utterances != summary.utterances:
        raise InputError("Transcript đã có thay đổi. Tạo tóm tắt từ phiên bản mới trước khi duyệt hoặc đặt lịch.", "REVISION_CONFLICT")
    if not revision.roles_confirmed or not revision.transcript_reviewed or any(t["role"] == "unknown" for t in revision.utterances):
        raise InputError("Cần nghe đối chiếu transcript và xác nhận vai trò trước khi duyệt/đặt lịch.", "ROLES_UNCONFIRMED")
    from consultation_quality.models import AudioSample
    if AudioSample.objects.filter(conversation=revision.conversation, review_disposition__in=["no_speech", "unclear"]).exists():
        raise InputError("Bản ghi chưa đủ điều kiện để xác nhận nội dung.")


def appointment_fields(data, summary):
    result = {}
    for field, limit in (("title", 200), ("participant", 200), ("responsible", 200), ("location", 500)):
        value = data.get(field, "")
        if not isinstance(value, str) or len(value) > limit or any(c in value for c in ("\r", "\n", "\x00")):
            raise InputError("Thông tin lịch không hợp lệ.")
        result[field] = value.strip()
    if not result["title"]:
        raise InputError("Cần tiêu đề lịch.")
    channel = data.get("channel", "phone")
    if not isinstance(channel, str) or channel not in ("phone", "online", "onsite"):
        raise InputError("Hình thức hẹn không hợp lệ.")
    result["channel"] = channel
    start, end = data.get("starts_at"), data.get("ends_at")
    if start in (None, "") and end in (None, ""):
        result.update(starts_at=None, ends_at=None)
    else:
        try:
            if not isinstance(start, str) or not isinstance(end, str):
                raise ValueError()
            start, end = parse_datetime(start), parse_datetime(end)
            if start is None or end is None or timezone.is_naive(start) or timezone.is_naive(end) or not timedelta(0) < end - start <= timedelta(hours=8):
                raise ValueError()
        except (ValueError, TypeError):
            raise InputError("Nhập giờ bắt đầu/kết thúc có múi giờ; thời lượng phải lớn hơn 0 và tối đa 8 giờ.") from None
        result.update(starts_at=start, ends_at=end)
    ids = data.get("evidence_ids", [])
    valid = {t["id"] for t in summary.utterances}
    if not isinstance(ids, list) or any(not isinstance(i, str) or i not in valid for i in ids):
        raise InputError("Dẫn chứng lịch phải thuộc phiên bản hội thoại này.", "INVALID_EVIDENCE")
    result["evidence_ids"] = list(dict.fromkeys(ids))
    return result
