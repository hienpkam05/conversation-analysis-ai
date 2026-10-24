from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from consultation_quality.access import can_review, visible_conversations
from consultation_quality.models import Conversation, Revision
from consultation_quality.services import InputError
from consultation_quality.views import body, endpoint
from .models import StatusDecision
from .services import LABELS, LABEL_MAP, TAXONOMY_VERSION, check_confirmable, is_stale, manual_fields, suggest


def rows_for(user):
    return StatusDecision.objects.filter(revision__conversation__in=visible_conversations(user)).select_related("revision__conversation", "author", "confirmed_by")


def serialize(row):
    from .review import review_json
    review = row.training_review if hasattr(row, "training_review") else None
    return {"id": str(row.pk), "revision_id": str(row.revision_id), "revision_hash": row.revision_hash,
        "utterances": row.utterances, "taxonomy_version": row.taxonomy_version, "source": row.source,
        "label": row.label, "evidence_ids": row.evidence_ids, "rationale": row.rationale, "metadata": row.metadata,
        "status": row.status, "version": row.version, "author": row.author.get_username(), "author_id": row.author_id,
        "confirmed_by": row.confirmed_by.get_username() if row.confirmed_by else None,
        "confirmed_at": row.confirmed_at.isoformat() if row.confirmed_at else None,
        "supersedes_id": str(row.supersedes_id) if row.supersedes_id else None,
        "created_at": row.created_at.isoformat(), "stale": is_stale(row),
        "suggested_next_step": LABEL_MAP[row.label]["next_step"], "training_review": review_json(review) if review else None}


@endpoint(["GET"])
def config(request):
    from .inference import model_status
    from .review import approval
    status = model_status()
    return JsonResponse({"taxonomy_version": TAXONOMY_VERSION, "labels": LABELS, "provider": "rules", "model_available": status["available"], "model": status, "taxonomy_approved": approval() is not None, "confidence": None})


@endpoint(["GET", "POST"])
def decisions(request, id):
    allowed = visible_conversations(request.user)
    revision = get_object_or_404(Revision.objects.select_related("conversation"), pk=id, conversation__in=allowed)
    if request.method == "GET":
        rows = rows_for(request.user).filter(revision=revision)
        latest_confirmed = rows.filter(status="confirmed").order_by("-confirmed_at", "-pk").first()
        current = serialize(latest_confirmed) if latest_confirmed else None
        if current and current["stale"]:
            current = None
        return JsonResponse({"items": [serialize(row) for row in rows.order_by("-created_at", "-pk")[:100]], "current_confirmed": current})
    data = body(request)
    source = data.get("source")
    snapshot_hash = revision.content_hash
    if source == "model":
        from .inference import predict
        # Native model work runs outside the DB transaction. Recheck source/access before saving.
        values = predict(revision.utterances)
    with transaction.atomic():
        Conversation.objects.select_for_update().get(pk=revision.conversation_id)
        revision = get_object_or_404(Revision.objects.select_for_update(), pk=id, conversation__in=visible_conversations(request.user))
        supersedes = None
        if source == "model":
            if revision.content_hash != snapshot_hash:
                raise InputError("Nguồn đã đổi trong lúc model xử lý; không lưu dự đoán.", "REVISION_CONFLICT")
        elif source == "rules":
            values = suggest(revision.utterances)
        elif source == "manual":
            values = dict(manual_fields(data, revision.utterances), metadata={"method": "human-label-v1", "confidence": None})
            if data.get("supersedes_id"):
                supersedes = get_object_or_404(rows_for(request.user), pk=data["supersedes_id"], revision=revision)
        else:
            raise InputError("Nguồn phải là rules, manual hoặc model.")
        from consultation_quality.training_data import digest
        from .review import definitions
        row = StatusDecision.objects.create(revision=revision, revision_hash=revision.content_hash, utterances=revision.utterances,
            taxonomy_version=TAXONOMY_VERSION, taxonomy_hash=digest(definitions()), author=request.user, source=source, supersedes=supersedes, **values)
    return JsonResponse(serialize(row), status=201)


@endpoint(["POST"])
@transaction.atomic
def confirm(request, id):
    row = get_object_or_404(rows_for(request.user).select_for_update(), pk=id)
    if row.author_id != request.user.pk and not can_review(request.user):
        raise InputError("Chỉ người tạo hoặc người có quyền duyệt được xác nhận.", "FORBIDDEN")
    data = body(request)
    if row.source == "model":
        raise InputError("Dự đoán AI chưa có dẫn chứng kiểm chứng; tạo bản thủ công và đối chiếu trước.")
    if data.get("confirmed_content") is not True:
        raise InputError("Cần xác nhận đã đối chiếu trạng thái với hội thoại.")
    if type(data.get("expected_version")) is not int or data["expected_version"] != row.version:
        raise InputError("Bản phân loại đã đổi; tải lại trước khi xác nhận.", "REVISION_CONFLICT")
    Conversation.objects.select_for_update().get(pk=row.revision.conversation_id)
    Revision.objects.select_for_update().get(pk=row.revision_id)
    row.revision.refresh_from_db()
    check_confirmable(row)
    if row.status != "confirmed":
        row.status, row.confirmed_by, row.confirmed_at = "confirmed", request.user, timezone.now()
        row.version += 1
        row.save()
        row.revision.status = "sealed"
        row.revision.save()
    return JsonResponse(serialize(row))
