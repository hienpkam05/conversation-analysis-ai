import uuid
from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from consultation_quality.access import can_review, visible_conversations
from consultation_quality.models import Conversation, Revision
from consultation_quality.services import InputError
from consultation_quality.views import body, endpoint
from .models import Appointment, AppointmentEvent, Summary
from .services import CATEGORIES, appointment_fields, check_current, extract, validate_sections


def summaries_for(user):
    return Summary.objects.filter(revision__conversation__in=visible_conversations(user))


def editable(user, owner_id):
    if user.pk != owner_id and not can_review(user):
        raise InputError("Chỉ người tạo hoặc người phụ trách được sửa/xác nhận.", "FORBIDDEN")


def summary_json(row):
    latest = row.revision.conversation.revisions.order_by("-revision_number").first()
    return {"id": str(row.pk), "revision_id": str(row.revision_id), "conversation_id": str(row.revision.conversation_id),
        "sections": row.sections, "utterances": row.utterances, "metadata": row.metadata, "source": row.source, "status": row.status,
        "version": row.version, "author": row.author.get_username(), "author_id": row.author_id,
        "reviewed_by": row.reviewed_by.get_username() if row.reviewed_by else None,
        "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
        "stale": latest.pk != row.revision_id or row.revision.content_hash != row.revision_hash,
        "created_at": row.created_at.isoformat(), "categories": CATEGORIES}


def appointment_json(row):
    return {"id": str(row.pk), "summary_id": str(row.summary_id), "owner_id": row.owner_id,
        "title": row.title, "participant": row.participant, "responsible": row.responsible, "channel": row.channel,
        "location": row.location, "starts_at": row.starts_at.isoformat() if row.starts_at else None,
        "ends_at": row.ends_at.isoformat() if row.ends_at else None, "evidence_ids": row.evidence_ids,
        "status": row.status, "version": row.version, "confirmed_by": row.confirmed_by.get_username() if row.confirmed_by else None,
        "confirmed_at": row.confirmed_at.isoformat() if row.confirmed_at else None,
        "events": [{"action": e.action, "actor": e.actor.get_username(), "created_at": e.created_at.isoformat()} for e in row.events.order_by("created_at")]}


def record(row, user, action):
    snapshot = appointment_json(row)
    snapshot.pop("events")
    AppointmentEvent.objects.create(appointment=row, actor=user, action=action, snapshot=snapshot)


@endpoint(["GET", "POST"])
def summaries(request, id):
    revision = get_object_or_404(Revision, pk=id, conversation__in=visible_conversations(request.user))
    if request.method == "GET":
        return JsonResponse({"items": [summary_json(s) for s in summaries_for(request.user).filter(revision=revision).order_by("-created_at")[:50]]})
    with transaction.atomic():
        revision = Revision.objects.select_for_update().get(pk=id)
        # Recompute under the lock so snapshot/hash cannot refer to different drafts.
        sections, metadata = extract(revision.utterances)
        row = Summary.objects.create(revision=revision, revision_hash=revision.content_hash, utterances=revision.utterances,
            sections=sections, metadata=metadata, author=request.user)
    return JsonResponse(summary_json(row), status=201)


@endpoint(["GET", "PUT"])
@transaction.atomic
def summary_detail(request, id):
    row = get_object_or_404(summaries_for(request.user).select_for_update(), pk=id)
    if request.method == "GET":
        return JsonResponse(summary_json(row))
    editable(request.user, row.author_id)
    data = body(request)
    if row.status != "draft" or row.source != "manual":
        raise InputError("Tạo bản sửa thủ công riêng; bản trích dẫn hoặc đã duyệt không được ghi đè.", "REVISION_CONFLICT")
    if type(data.get("expected_version")) is not int or data["expected_version"] != row.version:
        raise InputError("Tóm tắt đã đổi. Mở lại trước khi lưu.", "REVISION_CONFLICT")
    row.sections = validate_sections(data.get("sections"), row.utterances)
    row.version += 1
    row.save()
    return JsonResponse(summary_json(row))


@endpoint(["POST"])
def copy_summary(request, id):
    old = get_object_or_404(summaries_for(request.user), pk=id)
    row = Summary.objects.create(revision=old.revision, revision_hash=old.revision_hash, utterances=old.utterances,
        sections=old.sections, metadata={"method": "manual-v1"}, source="manual", author=request.user, supersedes=old)
    return JsonResponse(summary_json(row), status=201)


@endpoint(["POST"])
@transaction.atomic
def approve_summary(request, id):
    row = get_object_or_404(summaries_for(request.user).select_for_update(), pk=id)
    editable(request.user, row.author_id)
    data = body(request)
    if data.get("confirmed_content") is not True:
        raise InputError("Cần xác nhận đã đối chiếu nội dung với lời thoại.")
    if type(data.get("expected_version")) is not int or data["expected_version"] != row.version:
        raise InputError("Bản tóm tắt đã thay đổi; mở lại trước khi duyệt.", "REVISION_CONFLICT")
    Conversation.objects.select_for_update().get(pk=row.revision.conversation_id)
    Revision.objects.select_for_update().get(pk=row.revision_id)
    row.revision.refresh_from_db()
    check_current(row)
    validate_sections(row.sections, row.utterances)
    if row.status != "approved":
        row.status, row.reviewed_by, row.reviewed_at = "approved", request.user, timezone.now()
        row.version += 1
        row.save()
        row.revision.status = "sealed"
        row.revision.save()
    return JsonResponse(summary_json(row))


@endpoint(["GET", "POST"])
@transaction.atomic
def appointments(request):
    if request.method == "GET":
        rows = Appointment.objects.filter(summary__in=summaries_for(request.user))
        if request.GET.get("summary_id"):
            rows = rows.filter(summary_id=request.GET["summary_id"])
        return JsonResponse({"items": [appointment_json(a) for a in rows.order_by("-created_at")[:100]]})
    data = body(request)
    summary = get_object_or_404(summaries_for(request.user), pk=data.get("summary_id"))
    try:
        key = uuid.UUID(data.get("request_key", ""))
    except (ValueError, TypeError, AttributeError):
        raise InputError("Cần request_key UUID để tránh tạo lịch trùng.") from None
    values = appointment_fields(data, summary)
    old = Appointment.objects.filter(owner=request.user, request_key=key).first()
    if old:
        if old.summary_id != summary.pk or any(getattr(old, k) != v for k, v in values.items()):
            raise InputError("Mã yêu cầu đã dùng cho nội dung khác.", "REVISION_CONFLICT")
        return JsonResponse(appointment_json(old), status=200)
    row = Appointment.objects.create(summary=summary, owner=request.user, request_key=key, **values)
    record(row, request.user, "created")
    return JsonResponse(appointment_json(row), status=201)


@endpoint(["PUT"])
@transaction.atomic
def edit_appointment(request, id):
    row = get_object_or_404(Appointment.objects.select_for_update(), pk=id, summary__in=summaries_for(request.user))
    editable(request.user, row.owner_id)
    data = body(request)
    if row.status != "draft" or type(data.get("expected_version")) is not int or data["expected_version"] != row.version:
        raise InputError("Chỉ sửa lịch nháp đúng phiên bản. Lịch đã xác nhận cần hủy và lập bản mới.", "REVISION_CONFLICT")
    for key, value in appointment_fields(data, row.summary).items():
        setattr(row, key, value)
    row.version += 1
    row.save()
    record(row, request.user, "updated")
    return JsonResponse(appointment_json(row))


@endpoint(["POST"])
@transaction.atomic
def confirm_appointment(request, id):
    row = get_object_or_404(Appointment.objects.select_for_update(), pk=id, summary__in=summaries_for(request.user))
    editable(request.user, row.owner_id)
    data = body(request)
    if data.get("confirmed_with_participants") is not True:
        raise InputError("Cần xác nhận đã thống nhất lịch với người tham gia.")
    if row.status == "confirmed":
        return JsonResponse(appointment_json(row))
    if row.status != "draft" or type(data.get("expected_version")) is not int or data.get("expected_version") != row.version:
        raise InputError("Lịch đã đổi hoặc bị hủy; mở lại để kiểm tra.", "REVISION_CONFLICT")
    summary = Summary.objects.select_for_update().get(pk=row.summary_id)
    Conversation.objects.select_for_update().get(pk=summary.revision.conversation_id)
    Revision.objects.select_for_update().get(pk=summary.revision_id)
    summary.revision.refresh_from_db()
    check_current(summary)
    if summary.status != "approved":
        raise InputError("Duyệt bản tóm tắt trước khi xác nhận lịch.")
    if not row.participant or not row.responsible or not row.location or not row.starts_at or not row.ends_at or row.starts_at <= timezone.now():
        raise InputError("Cần người tham gia, người phụ trách, nơi/kênh liên hệ và giờ hẹn rõ ràng trong tương lai.")
    roles = {t["role"] for t in summary.utterances if t["id"] in row.evidence_ids}
    if not {"candidate", "consultant"} <= roles:
        raise InputError("Chọn lời của cả ứng viên và tư vấn viên để đối chiếu lịch.", "INVALID_EVIDENCE")
    get_user_model().objects.select_for_update().get(pk=row.owner_id)
    if Appointment.objects.filter(owner_id=row.owner_id, status="confirmed", starts_at__lt=row.ends_at, ends_at__gt=row.starts_at).exclude(pk=row.pk).exists():
        raise InputError("Tài khoản tạo lịch đã có lịch xác nhận trùng thời gian.", "REVISION_CONFLICT")
    row.status, row.confirmed_by, row.confirmed_at = "confirmed", request.user, timezone.now()
    row.version += 1
    row.save()
    record(row, request.user, "confirmed")
    return JsonResponse(appointment_json(row))


@endpoint(["POST"])
@transaction.atomic
def cancel_appointment(request, id):
    row = get_object_or_404(Appointment.objects.select_for_update(), pk=id, summary__in=summaries_for(request.user))
    editable(request.user, row.owner_id)
    if row.status != "cancelled":
        row.status = "cancelled"
        row.version += 1
        row.save()
        record(row, request.user, "cancelled")
    return JsonResponse(appointment_json(row))
