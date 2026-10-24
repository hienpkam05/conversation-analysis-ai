from collections import Counter

from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from consultation_quality.access import can_review
from consultation_quality.models import Conversation, Revision
from consultation_quality.services import InputError
from consultation_quality.training_data import digest
from consultation_quality.views import body, endpoint
from .models import LabelReview, StatusDecision, TaxonomyApproval
from .services import LABELS, TAXONOMY_VERSION, check_confirmable


def definitions():
    return {"version": TAXONOMY_VERSION, "labels": LABELS}


def approval():
    return TaxonomyApproval.objects.filter(version=TAXONOMY_VERSION, definition_hash=digest(definitions())).first()


def reviewer_only(user):
    if not can_review(user):
        raise InputError("Chỉ người phụ trách được duyệt nhãn hoặc xem báo cáo train.", "FORBIDDEN")


def note(data):
    value = data.get("note")
    if not isinstance(value, str) or not value.strip() or len(value) > 5000:
        raise InputError("Cần ghi chú duyệt từ 1 đến 5000 ký tự.")
    return value.strip()


def review_json(row):
    return {"verdict": row.verdict, "reviewer": row.reviewer.get_username(), "note": row.note, "created_at": row.created_at.isoformat()}


def taxonomy_payload():
    row = approval()
    return {"definitions": definitions(), "definition_hash": digest(definitions()),
        "approval": {"reviewer": row.reviewer.get_username(), "note": row.note, "created_at": row.created_at.isoformat()} if row else None}


@endpoint(["GET"])
def taxonomy(request):
    return JsonResponse(taxonomy_payload())


@endpoint(["POST"])
@transaction.atomic
def approve_taxonomy(request):
    reviewer_only(request.user)
    data = body(request)
    if data.get("confirmed_definitions") is not True or data.get("definition_hash") != digest(definitions()):
        raise InputError("Đọc và xác nhận đúng phiên bản định nghĩa trước khi duyệt.")
    text = note(data)
    if TaxonomyApproval.objects.filter(version=TAXONOMY_VERSION).exists():
        raise InputError("Phiên bản bộ nhãn đã có audit phê duyệt; không ghi đè.", "REVISION_CONFLICT")
    TaxonomyApproval.objects.create(version=TAXONOMY_VERSION, definition_hash=digest(definitions()), definitions=definitions(), reviewer=request.user, note=text)
    return JsonResponse(taxonomy_payload())


@endpoint(["POST"])
@transaction.atomic
def review_label(request, id):
    reviewer_only(request.user)
    row = get_object_or_404(StatusDecision.objects.select_for_update().select_related("revision__conversation"), pk=id)
    data = body(request)
    if row.author_id == request.user.pk:
        raise InputError("Không tự duyệt nhãn của mình thành dữ liệu train.", "FORBIDDEN")
    if row.source != "manual" or row.status != "confirmed" or row.taxonomy_version != TAXONOMY_VERSION:
        raise InputError("Chỉ duyệt bản thủ công đã xác nhận đúng phiên bản bộ nhãn.")
    if not approval():
        raise InputError("Bộ nhãn chưa được duyệt.")
    if type(data.get("expected_version")) is not int or data["expected_version"] != row.version:
        raise InputError("Phiên bản đã đổi; mở lại trước khi duyệt.", "REVISION_CONFLICT")
    if LabelReview.objects.filter(decision=row).exists():
        raise InputError("Bản này đã có kết quả duyệt; tạo bản sửa mới nếu cần.", "REVISION_CONFLICT")
    Conversation.objects.select_for_update().get(pk=row.revision.conversation_id)
    Revision.objects.select_for_update().get(pk=row.revision_id)
    row.revision.refresh_from_db()
    check_confirmable(row)
    verdict = data.get("verdict")
    if verdict not in ("approved", "rejected"):
        raise InputError("Kết quả duyệt không hợp lệ.")
    result = LabelReview.objects.create(decision=row, reviewer=request.user, verdict=verdict, note=note(data))
    return JsonResponse(review_json(result), status=201)


def training_status():
    from .dataset import eligible
    entries, excluded = eligible(require_approval=False)
    return {"taxonomy_approved": approval() is not None, "decisions": StatusDecision.objects.count(),
        "confirmed": StatusDecision.objects.filter(status="confirmed").count(),
        "reviews": dict(Counter(LabelReview.objects.values_list("verdict", flat=True))),
        "eligible": len(entries), "label_counts": dict(Counter(row.label for row in entries)), "excluded_counts": excluded,
        "unreviewed_transcripts": Revision.objects.exclude(transcript_reviewed=True, roles_confirmed=True).count(),
        "note": "Chỉ nhãn thủ công được người khác duyệt, nguồn hiện hành và bộ nhãn đã duyệt mới xuất được. Chưa có dữ liệu thì không train."}


@endpoint(["GET"])
def training_report(request):
    reviewer_only(request.user)
    return JsonResponse(training_status())
