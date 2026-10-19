import uuid
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth import get_user_model

from .access import can_review, visible_conversations
from .inference import InferenceError, LocalProvider, check_compatibility, normalize_output, read_spec
from .models import Assessment, AssessmentJob, QualityWorkerSlot, Revision, RubricVersion
from .services import InputError, validate_utterances
from .training_data import definitions, digest


def visible_jobs(user):
    rows = AssessmentJob.objects.filter(revision__conversation__in=visible_conversations(user))
    return rows if can_review(user) else rows.filter(requested_by=user)


def assessment_visible(user, assessment):
    return can_review(user) or assessment.author_id == user.pk or (
        assessment.source == "model" and AssessmentJob.objects.filter(assessment=assessment, requested_by=user).exists())


def check_revision(revision):
    from .review_views import ensure_assessable
    if revision.status != "sealed":
        raise InputError("Khóa bản hội thoại trước khi gửi chấm AI.", "REVISION_SEALED")
    ensure_assessable(revision)
    validate_utterances(revision.utterances)
    if not revision.utterances or any(t["role"] == "unknown" for t in revision.utterances):
        raise InputError("Cần nội dung và vai trò đã được kiểm tra.", "ROLES_UNCONFIRMED")


def check_access(job):
    user = get_user_model().objects.get(pk=job.requested_by_id)
    if not user.is_active or not (can_review(user) or user.has_perm("consultation_quality.annotate_quality")) or not visible_conversations(user).filter(pk=job.revision.conversation_id).exists():
        raise InferenceError("ACCESS_REVOKED")


@transaction.atomic
def enqueue(user, revision_id, data):
    # Match publication lock order (slot -> revision -> rubric) on databases with row locks.
    QualityWorkerSlot.objects.select_for_update().get(pk=1)
    revision = Revision.objects.select_for_update().get(pk=revision_id, conversation__in=visible_conversations(user))
    try:
        key = uuid.UUID(data.get("request_key", ""))
    except (ValueError, TypeError, AttributeError):
        raise InputError("Cần request_key UUID để không gửi trùng tác vụ.") from None
    rubric = RubricVersion.objects.select_for_update().get(pk=data.get("rubric_id"))
    existing = AssessmentJob.objects.filter(requested_by=user, request_key=key).first()
    if existing:
        if existing.revision_id != revision.pk or existing.rubric_id != rubric.pk:
            raise InputError("Mã yêu cầu đã dùng cho hội thoại hoặc rubric khác.", "REVISION_CONFLICT")
        return existing
    check_revision(revision)
    if rubric.status != "approved":
        raise InferenceError("RUBRIC_NOT_APPROVED")
    from .inference import status
    state = status()
    if not state["available"]:
        raise InferenceError(state["code"])
    _, spec, manifest_hash = read_spec()
    check_compatibility(spec, rubric)
    # Serialize queue admission separately from the worker lease; never hold a lock during inference.
    active = AssessmentJob.objects.filter(status__in=["queued", "running"])
    existing = active.filter(requested_by=user, revision=revision, rubric=rubric, manifest_hash=manifest_hash).first()
    if existing:
        return existing
    if active.count() >= settings.QUALITY_QUEUE_LIMIT or active.filter(requested_by=user).count() >= settings.QUALITY_USER_QUEUE_LIMIT:
        raise InputError("Hàng đợi đang đầy. Đợi tác vụ hiện tại hoàn tất rồi thử lại.", "QUEUE_FULL")
    return AssessmentJob.objects.create(revision=revision, rubric=rubric, requested_by=user, request_key=key,
        model_version=spec["model_version"], preprocessing_version=spec["preprocessing_version"], manifest_hash=manifest_hash,
        revision_hash=revision.content_hash, rubric_hash=digest(definitions(rubric.criteria_json)))


@transaction.atomic
def claim_job():
    now = timezone.now()
    token = uuid.uuid4()
    acquired = QualityWorkerSlot.objects.filter(pk=1).filter(Q(lease_until__isnull=True) | Q(lease_until__lt=now)).update(
        token=token, lease_until=now + timedelta(seconds=settings.QUALITY_JOB_TIMEOUT + 60), last_seen=now)
    if not acquired:
        return None
    # A terminated supervisor cannot publish a result after its lease has been replaced.
    AssessmentJob.objects.filter(status="running").update(status="failed", error_code="WORKER_INTERRUPTED", finished_at=now)
    job = AssessmentJob.objects.select_for_update().filter(status="queued").order_by("created_at", "id").first()
    if not job:
        QualityWorkerSlot.objects.filter(pk=1, token=token).update(token=None, lease_until=None)
        return None
    job.status, job.started_at, job.worker_token = "running", now, token
    job.save(update_fields=["status", "started_at", "worker_token"])
    return job.pk, token


def release_slot(token):
    QualityWorkerSlot.objects.filter(pk=1, token=token).update(token=None, lease_until=None, last_seen=timezone.now())


@transaction.atomic
def fail_job(job_id, token, code):
    QualityWorkerSlot.objects.select_for_update().get(pk=1)
    AssessmentJob.objects.filter(pk=job_id, status="running", worker_token=token).update(status="failed", error_code=code, finished_at=timezone.now())
    release_slot(token)


def execute_job(job_id, token):
    try:
        job = AssessmentJob.objects.select_related("revision", "rubric", "requested_by").get(pk=job_id, status="running", worker_token=token)
        root, spec, manifest_hash = read_spec()
        if job.manifest_hash != manifest_hash:
            raise InferenceError("MODEL_CHANGED")
        check_compatibility(spec, job.rubric)
        if job.rubric.status != "approved":
            raise InferenceError("RUBRIC_NOT_APPROVED")
        check_access(job)
        if job.revision.content_hash != job.revision_hash or digest(definitions(job.rubric.criteria_json)) != job.rubric_hash:
            raise InferenceError("REVISION_CHANGED")
        check_revision(job.revision)

        def progress(done, total):
            if not AssessmentJob.objects.filter(pk=job_id, status="running", worker_token=token).update(completed_windows=done, total_windows=total):
                raise InferenceError("WORKER_INTERRUPTED")
            QualityWorkerSlot.objects.filter(pk=1, token=token).update(last_seen=timezone.now())

        result = LocalProvider(root, spec).predict(job.revision.utterances, progress)
        ratings, metadata = normalize_output(result, spec, job.revision.utterances, job.rubric.criteria_json)
        with transaction.atomic():
            slot = QualityWorkerSlot.objects.select_for_update().get(pk=1)
            current = AssessmentJob.objects.select_for_update().get(pk=job_id)
            revision = Revision.objects.select_for_update().get(pk=job.revision_id)
            rubric = RubricVersion.objects.select_for_update().get(pk=job.rubric_id)
            if slot.token != token or slot.lease_until is None or slot.lease_until <= timezone.now() or current.status != "running" or current.worker_token != token:
                raise InferenceError("WORKER_INTERRUPTED")
            if revision.content_hash != job.revision_hash or digest(definitions(rubric.criteria_json)) != job.rubric_hash:
                raise InferenceError("REVISION_CHANGED")
            check_revision(revision)
            if rubric.status != "approved":
                raise InferenceError("RUBRIC_NOT_APPROVED")
            check_access(job)
            if read_spec()[2] != job.manifest_hash:
                raise InferenceError("MODEL_CHANGED")
            # No automatic evidence extractor is approved yet; never give these scores a complete total.
            assessment = Assessment.objects.create(revision=revision, rubric=dict(rubric.criteria_json, status=rubric.status),
                rubric_version=rubric, source="model", status="needs_review", ratings=ratings, total_score=None,
                model_version=job.model_version, preprocessing_version=job.preprocessing_version, inference_metadata=metadata)
            current.status, current.assessment, current.finished_at = "succeeded", assessment, timezone.now()
            current.completed_windows = current.total_windows = result["windows"]
            current.save(update_fields=["status", "assessment", "finished_at", "completed_windows", "total_windows"])
        release_slot(token)
    except AssessmentJob.DoesNotExist:
        release_slot(token)
    except InferenceError as exc:
        fail_job(job_id, token, exc.code)
    except InputError as exc:
        fail_job(job_id, token, "REVISION_CHANGED" if exc.code in ("REVISION_SEALED", "ROLES_UNCONFIRMED") else "MODEL_OUTPUT_INVALID")
    except Exception:
        # Do not expose exception strings: third-party errors may include transcript text or local paths.
        fail_job(job_id, token, "MODEL_INFERENCE_FAILED")
