import re

from consultation_quality.services import InputError, validate_utterances
from consultation_quality.models import AudioSample

FIELDS = [
    {"code": "full_name", "title": "Họ tên", "type": "text", "limit": 150},
    {"code": "phone", "title": "Số điện thoại", "type": "text", "limit": 30},
    {"code": "residence", "title": "Nơi ở hiện tại", "type": "text", "limit": 300},
    {"code": "desired_location", "title": "Nơi muốn làm việc", "type": "text", "limit": 300},
    {"code": "region", "title": "Vùng muốn làm việc", "type": "choice", "choices": {"north": "Miền Bắc", "central": "Miền Trung", "south": "Miền Nam"}},
    {"code": "desired_job", "title": "Công việc mong muốn", "type": "text", "limit": 500},
    {"code": "experience", "title": "Kinh nghiệm", "type": "text", "limit": 1000},
    {"code": "shift", "title": "Ca làm mong muốn", "type": "choice", "choices": {"day": "Ca ngày", "night": "Ca đêm", "rotating": "Xoay ca"}},
    {"code": "expected_salary", "title": "Lương mong muốn (VND/tháng)", "type": "number"},
    {"code": "availability", "title": "Thời điểm có thể đi làm", "type": "text", "limit": 500},
]
FIELD_MAP = {item["code"]: item for item in FIELDS}


def empty_fields():
    return [{"code": f["code"], "value": None, "evidence": [], "options": [], "conflict": False, "note": ""} for f in FIELDS]


def span(turn, start, end):
    return {"utterance_id": turn["id"], "start": start, "end": end, "quote": turn["text"][start:end]}


def extract(turns):
    turns = validate_utterances(turns)
    found = {code: [] for code in FIELD_MAP}
    overflow = set()

    def add(code, value, turn, start, end):
        if len(found[code]) < 20:
            found[code].append({"value": value, "evidence": [span(turn, start, end)]})
        else:
            overflow.add(code)

    patterns = {
        "residence": r"(?:tôi|chị|anh|em|mình)\s+(?:đang\s+)?(?:ở|sống ở)\s+([^,.!?;\n]{2,100})",
        "desired_location": r"(?:muốn|mong muốn)\s+(?:làm|làm việc)\s+(?:ở|tại)\s+([^,.!?;\n]{2,100})",
        "desired_job": r"(?:muốn|mong muốn)\s+(?:làm|ứng tuyển)\s+(?!\s*(?:ở\b|tại\b|việc ở\b|việc tại\b))([^,.!?;\n]{2,120})",
        "experience": r"(?:kinh nghiệm\s+(?:làm|về)|đã từng làm)\s+([^,.!?;\n]{2,150})",
        "availability": r"(?:có thể|sẵn sàng)\s+(?:đi làm|bắt đầu làm)\s+([^,.!?;\n]{2,100})",
    }
    for turn in turns:
        if turn["role"] != "candidate" or turn.get("unclear"):
            continue
        text = turn["text"]
        if re.search(r"\b(?:nếu|giả sử|người ta|bạn tôi|chị ấy|anh ấy)\b|[?\"“”]", text, re.I):
            continue
        for code, pattern in patterns.items():
            if code in ("desired_job", "desired_location") and re.search(r"không\s+(?:muốn|mong muốn|thích)", text, re.I):
                continue
            for match in re.finditer(pattern, text, re.I):
                value = re.split(r"\s+(?:và (?:tôi|chị|anh|em|mình)|hiện|nhưng|rồi)\s+", match.group(1), maxsplit=1, flags=re.I)[0].strip()
                if code == "desired_job" and re.match(r"(?:ca ngày|ca đêm|xoay ca)\b", value, re.I):
                    continue
                add(code, value, turn, match.start(1), match.start(1) + len(value))
        name_pattern = r"(?i:(?:tên (?:tôi|chị|anh|em|mình) là|(?:tôi|chị|anh|em|mình) tên là))\s+([A-ZÀ-ỸĐ][a-zà-ỹđ]+(?:\s+[A-ZÀ-ỸĐ][a-zà-ỹđ]+){0,5})"
        for match in re.finditer(name_pattern, text):
            words = list(re.finditer(r"[^\W\d_]+", match.group(1)))
            end = 0
            for word in words:
                if not word.group()[0].isupper():
                    break
                end = word.end()
            if end:
                add("full_name", match.group(1)[:end], turn, match.start(1), match.start(1) + end)
        if re.search(r"(?:số (?:điện thoại|của (?:tôi|chị|anh|em))|liên hệ (?:tôi|chị|anh|em))", text, re.I):
            for match in re.finditer(r"(?<!\w)(?:\+84|0)(?:[ .-]*\d){9}(?![ .-]*\d)(?!\w)", text):
                digits = re.sub(r"[ .-]", "", match.group())
                if digits.startswith("+84"):
                    digits = "0" + digits[3:]
                if re.fullmatch(r"0\d{9}", digits):
                    add("phone", digits, turn, match.start(), match.end())
        if not re.search(r"không\s+(?:muốn|làm|thích)|chưa\s+(?:muốn|chốt)", text, re.I) and re.search(r"muốn|mong muốn|chỉ làm", text, re.I):
            for code, pattern in (("day", r"ca ngày"), ("night", r"ca đêm"), ("rotating", r"xoay ca")):
                for match in re.finditer(pattern, text, re.I):
                    add("shift", code, turn, match.start(), match.end())
        # Salary is normalized only with explicit monthly units and an expectation cue.
        if re.search(r"(?:mong muốn|kỳ vọng|muốn lương|muốn mức lương)", text, re.I) and not re.search(r"không|chưa|từ\s+\d|đến\s+\d|\d\s*[-–]\s*\d", text, re.I):
            for match in re.finditer(r"(?<!\d)(\d{1,3}(?:[.,]\d{1,2})?)\s*triệu\s*(?:đồng\s*)?(?:/\s*tháng|một tháng|mỗi tháng|tháng)\b", text, re.I):
                salary = int(round(float(match.group(1).replace(",", ".")) * 1_000_000))
                if 0 < salary <= 1_000_000_000:
                    add("expected_salary", salary, turn, match.start(), match.end())
    fields = empty_fields()
    for field in fields:
        options = found[field["code"]]
        values = {str(option["value"]).casefold() for option in options}
        if field["code"] in overflow:
            field.update(conflict=True, options=options, note="Có quá nhiều thông tin cùng trường; cần kiểm tra thủ công.")
        elif len(values) == 1:
            field.update(value=options[0]["value"], evidence=options[0]["evidence"])
        elif len(values) > 1:
            field.update(conflict=True, options=options, note="Có nhiều giá trị; cần đối chiếu và chọn thủ công.")
    return fields


def validate_fields(fields, turns):
    if not isinstance(fields, list) or len(fields) != len(FIELDS) or any(not isinstance(f, dict) or not isinstance(f.get("code"), str) for f in fields) or {f["code"] for f in fields} != set(FIELD_MAP):
        raise InputError("Cần đúng bộ trường thông tin, không thiếu hoặc trùng mã.")
    by_id = {t["id"]: t for t in turns}
    clean = []
    for field in fields:
        code, value = field["code"], field.get("value")
        spec = FIELD_MAP[code]
        if value == "":
            value = None
        if value is not None:
            if spec["type"] == "number":
                if type(value) is not int or not 0 < value <= 1_000_000_000:
                    raise InputError("Lương mong muốn phải là số nguyên VND/tháng hợp lệ.")
            elif not isinstance(value, str) or not value.strip() or len(value) > spec.get("limit", 30) or any(c in value for c in ("\x00", "\r", "\n")):
                raise InputError("Giá trị thông tin không hợp lệ.")
            elif spec["type"] == "choice" and value not in spec["choices"]:
                raise InputError("Giá trị lựa chọn không hợp lệ.")
            if code == "phone" and not re.fullmatch(r"0\d{9}", value):
                raise InputError("Điện thoại cần định dạng 10 chữ số bắt đầu bằng 0.")
        evidence, note = field.get("evidence", []), field.get("note", "")
        if field.get("conflict") is not False or field.get("options", []) != []:
            raise InputError("Cần giải quyết xung đột và lưu bản thủ công riêng trước.")
        if not isinstance(note, str) or len(note) > 2000:
            raise InputError("Ghi chú mỗi trường tối đa 2000 ký tự.")
        if not isinstance(evidence, list) or len(evidence) > 10 or value is not None and not evidence:
            raise InputError("Trường có giá trị cần dẫn chứng ứng viên.", "INVALID_EVIDENCE")
        for item in evidence:
            if not isinstance(item, dict) or not isinstance(item.get("utterance_id"), str):
                raise InputError("Dẫn chứng không hợp lệ.", "INVALID_EVIDENCE")
            turn = by_id.get(item["utterance_id"])
            start, end = item.get("start"), item.get("end")
            if not turn or turn["role"] != "candidate" or turn.get("unclear") or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(turn["text"]) or item.get("quote") != turn["text"][start:end]:
                raise InputError("Dẫn chứng phải đúng vị trí/nguyên văn lời ứng viên nghe rõ.", "INVALID_EVIDENCE")
        clean.append({"code": code, "value": value.strip() if isinstance(value, str) else value, "evidence": evidence, "options": [], "conflict": False, "note": note.strip()})
    return clean


def stale(profile):
    latest = profile.revision.conversation.revisions.order_by("-revision_number").first()
    return latest.pk != profile.revision_id or profile.revision_hash != profile.revision.content_hash or profile.utterances != profile.revision.utterances


def check_confirmable(profile):
    if stale(profile):
        raise InputError("Transcript đã đổi; tạo bản thông tin từ phiên bản hiện hành.", "REVISION_CONFLICT")
    revision = profile.revision
    if not revision.transcript_reviewed or not revision.roles_confirmed or any(t["role"] == "unknown" for t in profile.utterances):
        raise InputError("Cần đối chiếu transcript và xác nhận vai người nói trước.")
    if AudioSample.objects.filter(conversation_id=revision.conversation_id, review_disposition__in=["no_speech", "unclear"]).exists():
        raise InputError("Bản ghi không đủ điều kiện xác nhận thông tin.")
    if profile.source != "manual":
        raise InputError("Tạo bản thủ công và đối chiếu thông tin trước khi xác nhận.")
    values = validate_fields(profile.fields, profile.utterances)
    if not any(f["value"] is not None for f in values):
        raise InputError("Chưa có thông tin nào để xác nhận.")
