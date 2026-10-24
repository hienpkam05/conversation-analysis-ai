import re
import unicodedata

from consultation_quality.models import AudioSample
from consultation_quality.services import InputError, validate_utterances


TAXONOMY_VERSION = "candidate-status-draft-v1"
LABELS = [
    {"code": "interested", "title": "Quan tâm", "description": "Có quan tâm, chưa cam kết phỏng vấn.", "next_step": "Trao đổi thêm nhu cầu và thông tin công việc."},
    {"code": "needs_information", "title": "Cần thêm thông tin", "description": "Cần làm rõ thông tin trước khi quyết định.", "next_step": "Giải đáp câu hỏi rồi xác nhận lại mong muốn."},
    {"code": "callback_requested", "title": "Muốn liên hệ lại", "description": "Đề nghị trao đổi vào dịp khác, chưa chốt phỏng vấn.", "next_step": "Hỏi thời điểm và kênh liên hệ phù hợp; chưa tự tạo lịch."},
    {"code": "interview_agreed", "title": "Đồng ý phỏng vấn", "description": "Đồng ý tham gia phỏng vấn, chưa chứng minh đã có lịch cụ thể.", "next_step": "Xác nhận lại thời gian, địa điểm và người liên hệ."},
    {"code": "declined", "title": "Từ chối", "description": "Từ chối cơ hội đang được trao đổi.", "next_step": "Đối chiếu lý do và phạm vi từ chối; không tự loại hồ sơ ứng viên."},
    {"code": "unknown", "title": "Chưa đủ căn cứ", "description": "Thiếu lời xác nhận, nguồn chưa rõ hoặc có thông tin mâu thuẫn.", "next_step": "Nghe lại và hỏi rõ trạng thái hiện tại của ứng viên."},
]
LABEL_MAP = {item["code"]: item for item in LABELS}


def normalize(text):
    value = unicodedata.normalize("NFD", text.casefold()).replace("đ", "d")
    return " ".join("".join(c for c in value if unicodedata.category(c) != "Mn").split())


# Explicit phrases only. Ambiguous/negative clauses abstain instead of implying consent.
PATTERNS = {
    "interested": r"\b(?:toi|chi|anh|em|minh) (?:rat )?(?:quan tam|muon tim hieu)\b",
    "needs_information": r"\b(?:cho (?:toi|chi|anh|em|minh) hoi|can (?:biet|them) thong tin|muon hoi them)\b",
    "callback_requested": r"\b(?:goi lai (?:cho )?(?:toi|chi|anh|em|minh)|(?:toi|chi|anh|em|minh) se goi lai|lien he lai (?:cho )?(?:toi|chi|anh|em|minh))\b",
    "interview_agreed": r"\b(?:toi|chi|anh|em|minh) (?:dong y (?:tham gia )?phong van|se (?:den|di|tham gia) phong van|nhan loi phong van)\b",
    "declined": r"\b(?:toi|chi|anh|em|minh) (?:khong (?:co nhu cau(?: nua)?|muon ung tuyen(?: nua)?|dong y (?:tham gia )?phong van|tham gia phong van)|tu choi (?:cong viec|vi tri|phong van|co hoi))\b",
}


def suggest(utterances):
    turns = validate_utterances(utterances)
    hits, ambiguous = [], []
    for turn in turns:
        if turn["role"] != "candidate" or turn.get("unclear"):
            continue
        text = normalize(turn["text"])
        # Quoted/reported, conditional, uncertain or question language is not a commitment.
        if re.search(r"\b(?:neu|gia su|chua|co le|chac|phan van|noi rang|bao rang|co noi|tung noi|truoc day|nhung|tuy nhien|khong chac|khong phai)\b|[\"“”]", text):
            if re.search(r"phong van|ung tuyen|nhu cau|quan tam|goi lai", text):
                ambiguous.append(turn["id"])
            continue
        labels = [label for label, pattern in PATTERNS.items() if re.search(pattern, text)]
        if "?" in text and labels != ["needs_information"]:
            if labels:
                ambiguous.append(turn["id"])
            continue
        if labels != ["declined"] and re.search(r"\b(?:khong|chang|chua|dung)\b", text):
            if re.search(r"phong van|ung tuyen|nhu cau|quan tam|goi lai", text):
                ambiguous.append(turn["id"])
            continue
        hits.extend({"label": label, "utterance_id": turn["id"]} for label in labels)
    found = {hit["label"] for hit in hits}
    evidence = list(dict.fromkeys([hit["utterance_id"] for hit in hits] + ambiguous))[:200]
    if len(found) == 1 and not ambiguous:
        label = next(iter(found))
        reason = "Có lời ứng viên khớp quy tắc. Cần nghe lại và xác nhận, không phải kết quả mô hình đã huấn luyện."
    else:
        label = "unknown"
        reason = "Có nhiều tín hiệu hoặc lời chưa chắc chắn; cần đối chiếu diễn biến và quyết định cuối." if found or ambiguous else "Chưa tìm được lời ứng viên đủ rõ theo bộ quy tắc hiện tại."
    return {"label": label, "evidence_ids": evidence, "rationale": reason,
        "metadata": {"method": "explicit-candidate-phrases-v1", "matches": hits, "ambiguous_ids": ambiguous, "confidence": None, "model_available": False}}


def manual_fields(data, utterances):
    label, ids, rationale = data.get("label"), data.get("evidence_ids"), data.get("rationale", "")
    if not isinstance(label, str) or label not in LABEL_MAP:
        raise InputError("Trạng thái không hợp lệ.")
    if not isinstance(rationale, str) or len(rationale) > 5000:
        raise InputError("Ghi chú không hợp lệ hoặc dài quá 5000 ký tự.")
    candidates = {t["id"] for t in utterances if t["role"] == "candidate" and not t.get("unclear")}
    if not isinstance(ids, list) or len(ids) > 200 or any(not isinstance(i, str) for i in ids) or len(set(ids)) != len(ids) or not set(ids) <= candidates:
        raise InputError("Chỉ chọn dẫn chứng ứng viên nghe rõ trong đúng phiên bản.", "INVALID_EVIDENCE")
    if label != "unknown" and not ids:
        raise InputError("Trạng thái cụ thể cần ít nhất một lời ứng viên làm căn cứ.", "INVALID_EVIDENCE")
    if label == "unknown" and not rationale.strip():
        raise InputError("Ghi lý do chưa đủ căn cứ.")
    return {"label": label, "evidence_ids": ids, "rationale": rationale.strip()}


def is_stale(row):
    revision = row.revision
    latest = revision.conversation.revisions.order_by("-revision_number").first()
    return latest.pk != revision.pk or revision.content_hash != row.revision_hash or revision.utterances != row.utterances


def check_confirmable(row):
    from consultation_quality.training_data import digest
    from .review import definitions
    if row.taxonomy_hash != digest(definitions()):
        raise InputError("Bản phân loại không còn khớp định nghĩa bộ nhãn; tạo bản mới.", "REVISION_CONFLICT")
    revision = row.revision
    if is_stale(row):
        raise InputError("Transcript đã đổi; tạo bản phân loại trên phiên bản mới nhất.", "REVISION_CONFLICT")
    if not revision.transcript_reviewed or not revision.roles_confirmed or any(t["role"] == "unknown" for t in row.utterances):
        raise InputError("Cần đối chiếu transcript và xác nhận vai người nói trước.")
    if AudioSample.objects.filter(conversation_id=revision.conversation_id, review_disposition__in=["no_speech", "unclear"]).exists():
        raise InputError("Bản ghi không có lời nói hoặc khó nghe; kiểm tra lại trước khi xác nhận.")
    manual_fields({"label": row.label, "evidence_ids": row.evidence_ids, "rationale": row.rationale}, row.utterances)
