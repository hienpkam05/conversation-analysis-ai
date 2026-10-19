from django.db import transaction
from django.http import JsonResponse

from .access import visible_conversations
from .inference import ERRORS, InferenceError, status
from .jobs import assessment_visible, enqueue, visible_jobs
from .models import Assessment, Revision
from .services import validate_ratings
from .views import assessment_json, body, endpoint


def job_json(job):
    return {"id": str(job.pk), "revision_id": str(job.revision_id), "rubric_id": str(job.rubric_id),
        "status": job.status, "model_version": job.model_version, "preprocessing_version": job.preprocessing_version,
        "completed_windows": job.completed_windows, "total_windows": job.total_windows,
        "assessment_id": str(job.assessment_id) if job.assessment_id else None,
        "created_at": job.created_at.isoformat(), "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "error": {"code": job.error_code, "message": ERRORS.get(job.error_code, ERRORS["MODEL_INFERENCE_FAILED"])} if job.status == "failed" else None}


@endpoint(["GET", "POST"])
def jobs(request, id):
    Revision.objects.get(pk=id, conversation__in=visible_conversations(request.user))
    if request.method == "GET":
        return JsonResponse({"items": [job_json(j) for j in visible_jobs(request.user).filter(revision_id=id).order_by("-created_at")[:20]]})
    state = status()
    if not state["available"]:
        raise InferenceError(state["code"])
    job = enqueue(request.user, id, body(request))
    return JsonResponse(job_json(job), status=202)


@endpoint(["GET"])
def job_detail(request, id):
    return JsonResponse(job_json(visible_jobs(request.user).get(pk=id)))


@endpoint(["POST"])
@transaction.atomic
def manual_copy(request, id):
    original = Assessment.objects.get(pk=id, source="model", revision__conversation__in=visible_conversations(request.user))
    if not assessment_visible(request.user, original):
        raise Assessment.DoesNotExist()
    ratings, _ = validate_ratings(original.ratings, original.revision.utterances, allow_incomplete=True, rubric=original.rubric)
    # Copies contain no model confidence metadata; their provenance remains linked via supersedes.
    result = Assessment.objects.create(revision=original.revision, rubric=original.rubric, rubric_version=original.rubric_version,
        ratings=ratings, total_score=None, source="manual", status="draft", supersedes=original, author=request.user)
    return JsonResponse(assessment_json(result), status=201)
