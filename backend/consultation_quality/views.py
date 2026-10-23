import json
from pathlib import Path
from functools import wraps
from django.conf import settings

from django.db import transaction, IntegrityError, OperationalError
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.http import JsonResponse, FileResponse, StreamingHttpResponse, Http404
from django.views.decorators.csrf import csrf_protect

from .models import Assessment, AudioSample, Conversation, Revision, RubricVersion, AssessmentJob
from .inference import InferenceError
from .access import can_review, visible_conversations
from .services import InputError, RUBRIC, transcript_review_flags, validate_ratings, validate_utterances


def endpoint(methods, public=False):
    def decorate(fn):
        @csrf_protect
        @wraps(fn)
        def wrapped(request, *args, **kwargs):
            if request.method not in methods:
                return JsonResponse({"error": {"code": "METHOD_NOT_ALLOWED", "message": "Phương thức không được hỗ trợ."}}, status=405)
            if not public and not request.user.is_authenticated:
                return JsonResponse({"error": {"code": "UNAUTHORIZED", "message": "Hãy đăng nhập để mở dữ liệu tư vấn."}}, status=401)
            if not public and not (can_review(request.user) or request.user.has_perm("consultation_quality.annotate_quality")):
                return JsonResponse({"error": {"code": "FORBIDDEN", "message": "Tài khoản chưa được cấp quyền chấm tư vấn."}}, status=403)
            try:
                return fn(request, *args, **kwargs)
            except (InputError, json.JSONDecodeError, UnicodeDecodeError, ValidationError) as exc:
                code = getattr(exc, "code", "INVALID_INPUT")
                status = {"INPUT_TOO_LARGE": 413, "REVISION_CONFLICT": 409, "REVISION_SEALED": 409,
                    "FORBIDDEN": 403, "UNAUTHORIZED": 401, "RUBRIC_LOCKED": 409, "QUEUE_FULL": 429}.get(code, 422)
                return JsonResponse({"error": {"code": code, "message": str(exc)}}, status=status)
            except InferenceError as exc:
                status = 409 if exc.code in ("RUBRIC_MODEL_MISMATCH", "MODEL_CHANGED") else 422 if exc.code == "RUBRIC_NOT_APPROVED" else 503
                return JsonResponse({"error": {"code": exc.code, "message": str(exc)}}, status=status)
            except (Http404, Conversation.DoesNotExist, Revision.DoesNotExist, Assessment.DoesNotExist, AudioSample.DoesNotExist, RubricVersion.DoesNotExist, AssessmentJob.DoesNotExist):
                return JsonResponse({"error": {"code": "NOT_FOUND", "message": "Không tìm thấy dữ liệu."}}, status=404)
            except IntegrityError:
                return JsonResponse({"error": {"code": "WRITE_CONFLICT", "message": "Dữ liệu vừa được thay đổi hoặc vi phạm ràng buộc. Tải lại trước khi lưu."}}, status=409)
            except OperationalError:
                return JsonResponse({"error": {"code": "DATABASE_UNAVAILABLE", "message": "Database chưa sẵn sàng hoặc đang bận. Thử lại sau."}}, status=503)
        return wrapped
    return decorate


def body(request):
    value = json.loads(request.body)
    if not isinstance(value, dict):
        raise InputError("Nội dung cần là một đối tượng JSON.")
    return value


def revision_json(revision):
    sample = AudioSample.objects.filter(conversation_id=revision.conversation_id).first()
    return {"id": str(revision.id), "conversation_id": str(revision.conversation_id), "title": revision.conversation.title, "utterances": revision.utterances, "roles_confirmed": revision.roles_confirmed, "transcript_reviewed": revision.transcript_reviewed, "source_type": revision.source_type,
            "status": revision.status, "revision_number": revision.revision_number, "content_hash": revision.content_hash,
            "audio_url": f"/api/quality/samples/{sample.id}/audio/" if sample else None,
            "review_flags": transcript_review_flags(revision.utterances, sample.transcript_metadata.get("raw_segments", []) if sample else [])}


def assessment_json(item):
    return {"id": str(item.id), "revision": revision_json(item.revision), "rubric": item.rubric, "ratings": item.ratings, "total_score": item.total_score, "source": item.source, "status": item.status, "created_at": item.created_at.isoformat(),
        "author": item.author.get_username() if item.author else None, "author_id": item.author_id,
        "reviewer": item.reviewer.get_username() if item.reviewer else None,
        "reviewed_at": item.reviewed_at.isoformat() if item.reviewed_at else None,
        "review_note": item.review_note, "supersedes_id": str(item.supersedes_id) if item.supersedes_id else None,
        "model_version": item.model_version or None, "preprocessing_version": item.preprocessing_version or None,
        "inference_metadata": item.inference_metadata}


@endpoint(["GET"])
def model_status(request):
    from .inference import status
    from .models import QualityWorkerSlot
    slot = QualityWorkerSlot.objects.filter(pk=1).first()
    return JsonResponse(dict(status(), worker_last_seen=slot.last_seen.isoformat() if slot and slot.last_seen else None,
        max_concurrency=1, timeout_seconds=settings.QUALITY_JOB_TIMEOUT))


@endpoint(["GET", "POST"])
def conversations(request):
    if request.method == "GET":
        try:
            offset, limit = int(request.GET.get("offset", 0)), int(request.GET.get("limit", 100))
            if offset < 0 or not 1 <= limit <= 100:
                raise ValueError()
        except ValueError:
            raise InputError("Phân trang không hợp lệ.")
        rows = visible_conversations(request.user).order_by("-created_at")
        return JsonResponse({"count": rows.count(), "offset": offset, "limit": limit, "items": [{"id": str(x.id), "title": x.title, "created_at": x.created_at.isoformat()} for x in rows[offset:offset + limit]]})
    data = body(request)
    utterances = validate_utterances(data.get("utterances"))
    title = data.get("title", "Hội thoại mới")
    source = data.get("source_type", "text")
    confirmed = data.get("roles_confirmed", False)
    reviewed = data.get("transcript_reviewed", False)
    if type(reviewed) is not bool:
        raise InputError("Xác nhận transcript không hợp lệ.")
    if not isinstance(title, str) or not title.strip() or len(title) > 200 or not isinstance(source, str) or source not in {"text", "stt"} or type(confirmed) is not bool:
        raise InputError("Tên, nguồn hoặc xác nhận vai trò không hợp lệ.")
    if confirmed and any(x["role"] == "unknown" for x in utterances):
        raise InputError("Còn lượt nói chưa rõ vai trò.", "ROLES_UNCONFIRMED")
    with transaction.atomic():
        conversation = Conversation.objects.create(title=title.strip(), owner=request.user, source_type=source)
        revision = Revision.objects.create(conversation=conversation, utterances=utterances, roles_confirmed=confirmed, transcript_reviewed=reviewed, source_type=source)
    return JsonResponse(revision_json(revision), status=201)


@endpoint(["GET"])
def conversation_detail(request, id):
    conversation = visible_conversations(request.user).get(id=id)
    revisions = conversation.revisions.order_by("-created_at")
    return JsonResponse({"id": str(id), "title": conversation.title, "revisions": [revision_json(x) for x in revisions]})


@endpoint(["POST"])
def new_revision(request, id):
    data = body(request)
    turns = validate_utterances(data.get("utterances"))
    confirmed, reviewed = data.get("roles_confirmed", False), data.get("transcript_reviewed", False)
    if type(confirmed) is not bool or type(reviewed) is not bool:
        raise InputError("Xác nhận không hợp lệ.")
    if confirmed and any(t["role"] == "unknown" for t in turns):
        raise InputError("Còn lượt nói chưa rõ vai trò.", "ROLES_UNCONFIRMED")
    with transaction.atomic():
        conversation = visible_conversations(request.user).select_for_update().get(id=id)
        latest = conversation.revisions.order_by("-created_at").first()
        if latest and data.get("expected_revision_id") != str(latest.id):
            raise InputError("Hội thoại đã có phiên bản mới. Hãy mở lại trước khi lưu.", "REVISION_CONFLICT")
        import uuid
        id_map = {t["id"]: str(uuid.uuid4()) for t in turns}
        turns = [dict(t, id=id_map[t["id"]]) for t in turns]
        revision = Revision.objects.create(conversation=conversation, utterances=turns, roles_confirmed=confirmed,
            transcript_reviewed=reviewed, source_type=latest.source_type if latest else "text")
    return JsonResponse(dict(revision_json(revision), utterance_id_map=id_map), status=201)


@endpoint(["GET", "POST"])
@transaction.atomic
def assessments(request, id):
    revision = Revision.objects.select_for_update().select_related("conversation").get(id=id, conversation__in=visible_conversations(request.user))
    if request.method == "GET":
        rows = revision.assessments.order_by("-created_at")
        if not can_review(request.user):
            rows = rows.filter(Q(author=request.user) | Q(source="model", ai_job__requested_by=request.user))
        return JsonResponse({"items": [assessment_json(x) for x in rows]})
    data = body(request)
    rubric = (RubricVersion.objects.select_for_update().get(id=data["rubric_id"]) if data.get("rubric_id")
        else RubricVersion.objects.select_for_update().get(version=data.get("rubric_version")))
    if data.get("rubric_version") and data["rubric_version"] != rubric.version:
        raise InputError("ID và mã phiên bản rubric không khớp.")
    if rubric.status == "retired":
        raise InputError("Bộ tiêu chí đã ngừng sử dụng.")
    status = data.get("status", "draft")
    if status not in ("draft", "needs_review"):
        raise InputError("Chỉ lưu nháp hoặc gửi chờ duyệt; chưa mở phê duyệt nhãn.")
    if status == "needs_review" and (not revision.roles_confirmed or not revision.transcript_reviewed):
        raise InputError("Hãy xác nhận transcript và vai trò trước khi hoàn tất bản chấm.", "ROLES_UNCONFIRMED")
    if status == "needs_review" and AudioSample.objects.filter(conversation_id=revision.conversation_id,
            review_disposition__in=["no_speech", "unclear"]).exists():
        raise InputError("Bản ghi đã đánh dấu không có lời nói hoặc khó nghe. Kiểm tra lại tình trạng trước khi hoàn tất chấm.", "AUDIO_NOT_ASSESSABLE")
    ratings, total = validate_ratings(data.get("ratings"), revision.utterances, allow_incomplete=status == "draft", rubric=rubric.criteria_json)
    supersedes = None
    if data.get("supersedes_id"):
        supersedes = revision.assessments.get(pk=data["supersedes_id"])
        from .jobs import assessment_visible
        if (supersedes.rubric_version_id != rubric.id or
                not (supersedes.author_id == request.user.id or supersedes.source == "model" and assessment_visible(request.user, supersedes))):
            raise InputError("Không thể thay thế bản chấm của người khác hoặc rubric khác.", "FORBIDDEN")
    item = Assessment.objects.create(revision=revision, rubric=dict(rubric.criteria_json, status=rubric.status),
        rubric_version=rubric, author=request.user, ratings=ratings, total_score=total, status=status, supersedes=supersedes)
    revision.refresh_from_db()
    return JsonResponse(assessment_json(item), status=201)


@endpoint(["GET"])
def samples(request):
    rows = AudioSample.objects.select_related("conversation").filter(conversation__in=visible_conversations(request.user)).order_by("call_id")
    items = []
    for sample in rows:
        latest = sample.conversation.revisions.order_by("-created_at").first()
        assessments = latest.assessments.all() if latest else Assessment.objects.none()
        if not can_review(request.user):
            assessments = assessments.filter(author=request.user)
        assessment = assessments.order_by("-created_at").first()
        items.append({"id": str(sample.id), "call_id": sample.call_id, "conversation_id": str(sample.conversation_id),
            "duration_seconds": sample.duration_seconds, "status": sample.status, "error_code": sample.error_code,
            "audio_url": f"/api/quality/samples/{sample.id}/audio/",
            "label_status": assessment.status if assessment else None,
            "review_disposition": sample.review_disposition, "review_note": sample.review_note})
    return JsonResponse({"items": items})


@endpoint(["POST"])
def review_sample(request, id):
    sample = AudioSample.objects.get(id=id, conversation__in=visible_conversations(request.user))
    data = body(request)
    disposition, note = data.get("disposition"), data.get("note", "")
    if disposition not in ("unreviewed", "usable", "no_speech", "unclear", "incomplete") or not isinstance(note, str) or len(note) > 5000:
        raise InputError("Tình trạng hoặc ghi chú không hợp lệ.")
    if disposition in ("no_speech", "unclear", "incomplete") and not note.strip():
        raise InputError("Hãy ghi lý do loại hoặc cần xem lại bản ghi.")
    sample.review_disposition, sample.review_note = disposition, note.strip()
    sample.save(update_fields=["review_disposition", "review_note", "updated_at"])
    return JsonResponse({"disposition": disposition, "note": note.strip(), "approved_for_training": False})


@endpoint(["GET"])
def audio(request, id):
    sample = AudioSample.objects.get(id=id, conversation__in=visible_conversations(request.user))
    path = Path(sample.source_path)
    if not path.is_file():
        return JsonResponse({"error": {"code": "AUDIO_MISSING", "message": "Không tìm thấy audio gốc trên máy."}}, status=404)
    size = path.stat().st_size
    byte_range = request.headers.get("Range")
    if not byte_range:
        response = FileResponse(path.open("rb"), content_type="audio/mpeg")
    else:
        try:
            unit, value = byte_range.split("=", 1)
            first, last = value.split("-", 1)
            if unit != "bytes" or "," in value:
                raise ValueError()
            start = int(first) if first else max(0, size - int(last))
            end = min(int(last), size - 1) if first and last else size - 1
            if not 0 <= start <= end < size:
                raise ValueError()
        except ValueError:
            response = StreamingHttpResponse(status=416)
            response["Content-Range"] = f"bytes */{size}"
            return response
        def chunks():
            with path.open("rb") as handle:
                handle.seek(start)
                remaining = end - start + 1
                while remaining:
                    chunk = handle.read(min(65536, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk
        response = StreamingHttpResponse(chunks(), status=206, content_type="audio/mpeg")
        response["Content-Range"] = f"bytes {start}-{end}/{size}"
        response["Content-Length"] = end - start + 1
    response["Accept-Ranges"] = "bytes"
    return response
