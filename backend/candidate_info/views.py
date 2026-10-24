from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from consultation_quality.access import can_review, visible_conversations
from consultation_quality.models import Conversation, Revision
from consultation_quality.services import InputError
from consultation_quality.views import body, endpoint
from . import matching
from .models import CampaignSearch, CandidateProfile
from .services import FIELDS, check_confirmable, extract, stale, validate_fields


def profiles_for(user):
    return CandidateProfile.objects.filter(revision__conversation__in=visible_conversations(user)).select_related("revision__conversation", "author", "confirmed_by")


def editable(user, row):
    if row.author_id != user.pk and not can_review(user):
        raise InputError("Chỉ tác giả hoặc người có quyền duyệt được xác nhận.", "FORBIDDEN")


def profile_json(row):
    return {"id": str(row.pk), "revision_id": str(row.revision_id), "utterances": row.utterances, "fields": row.fields,
        "source": row.source, "status": row.status, "version": row.version, "author": row.author.get_username(), "author_id": row.author_id,
        "confirmed_by": row.confirmed_by.get_username() if row.confirmed_by else None,
        "confirmed_at": row.confirmed_at.isoformat() if row.confirmed_at else None,
        "supersedes_id": str(row.supersedes_id) if row.supersedes_id else None, "stale": stale(row), "created_at": row.created_at.isoformat()}


def search_json(row):
    return {"id": str(row.pk), "profile_id": str(row.profile_id), "query": row.query, "result": row.result,
        "requested_by": row.requested_by.get_username(), "created_at": row.created_at.isoformat()}


@endpoint(["GET"])
def config(request):
    return JsonResponse({"fields": FIELDS, "extraction_provider": "rules", "ner_model_available": False})


@endpoint(["GET", "POST"])
@transaction.atomic
def profiles(request, id):
    revision = get_object_or_404(Revision.objects.select_related("conversation"), pk=id, conversation__in=visible_conversations(request.user))
    if request.method == "GET":
        return JsonResponse({"items": [profile_json(row) for row in profiles_for(request.user).filter(revision=revision).order_by("-created_at")[:100]]})
    Conversation.objects.select_for_update().get(pk=revision.conversation_id)
    revision = Revision.objects.select_for_update().get(pk=id)
    data = body(request)
    source, previous = data.get("source"), None
    if source == "rules":
        fields = extract(revision.utterances)
    elif source == "manual":
        fields = validate_fields(data.get("fields"), revision.utterances)
        if data.get("supersedes_id"):
            previous = get_object_or_404(profiles_for(request.user), pk=data["supersedes_id"], revision=revision)
    else:
        raise InputError("Nguồn phải là rules hoặc manual; chưa có PhoBERT NER đã train.")
    row = CandidateProfile.objects.create(revision=revision, revision_hash=revision.content_hash, utterances=revision.utterances,
        fields=fields, source=source, author=request.user, supersedes=previous)
    return JsonResponse(profile_json(row), status=201)


@endpoint(["POST"])
@transaction.atomic
def confirm(request, id):
    row = get_object_or_404(profiles_for(request.user).select_for_update(), pk=id)
    editable(request.user, row)
    data = body(request)
    if data.get("confirmed_content") is not True:
        raise InputError("Cần xác nhận đã đối chiếu từng thông tin và dẫn chứng.")
    if type(data.get("expected_version")) is not int or data["expected_version"] != row.version:
        raise InputError("Bản thông tin đã đổi; mở lại trước khi xác nhận.", "REVISION_CONFLICT")
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
    return JsonResponse(profile_json(row))


@endpoint(["GET", "POST"])
def searches(request, id):
    profile = get_object_or_404(profiles_for(request.user), pk=id)
    if request.method == "GET":
        return JsonResponse({"items": [search_json(row) for row in profile.searches.select_related("requested_by").order_by("-created_at")[:50]]})
    data = body(request)
    if data.get("confirmed_share") is not True:
        raise InputError("Cần xác nhận gửi thông tin nghề nghiệp để tìm chiến dịch.")
    check_confirmable(profile)
    if profile.status != "confirmed":
        raise InputError("Xác nhận bản thông tin trước khi gửi tìm kiếm.")
    query = matching.make_query(profile, data.get("top_k", 3), data.get("strict_salary", False))
    try:
        result = matching.search(query)
    except matching.MatchingUnavailable as exc:
        return JsonResponse({"error": {"code": exc.code, "message": str(exc)}}, status=503)
    with transaction.atomic():
        Conversation.objects.select_for_update().get(pk=profile.revision.conversation_id)
        Revision.objects.select_for_update().get(pk=profile.revision_id)
        profile = get_object_or_404(profiles_for(request.user), pk=id)
        check_confirmable(profile)
        row = CampaignSearch.objects.create(profile=profile, query=query, result=result, requested_by=request.user)
    return JsonResponse(search_json(row), status=201)
