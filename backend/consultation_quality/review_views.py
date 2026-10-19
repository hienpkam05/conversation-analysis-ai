import math
import re

from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.middleware.csrf import get_token
from django.http import JsonResponse
from django.utils import timezone

from .access import can_review, visible_conversations
from .models import Assessment, AudioSample, PilotResolution, Revision, RubricVersion
from .services import InputError, validate_ratings, validate_utterances
from .views import assessment_json, body, endpoint, revision_json


def require_reviewer(request):
    if not can_review(request.user):
        raise InputError("Chỉ người phụ trách mới có quyền duyệt.", "FORBIDDEN")


def csrf_failure(request, reason=""):
    return JsonResponse({"error": {"code": "CSRF_FAILED", "message": "Phiên xác thực hết hạn. Tải lại trang rồi thử lại."}}, status=403)


@endpoint(["GET", "POST", "DELETE"], public=True)
def session(request):
    if request.method == "POST":
        data = body(request)
        username, password = data.get("username"), data.get("password")
        if not isinstance(username, str) or not isinstance(password, str) or len(username) > 150 or len(password) > 1000:
            raise InputError("Thông tin đăng nhập không hợp lệ.")
        user = authenticate(request, username=username, password=password)
        if user is None:
            raise InputError("Tên đăng nhập hoặc mật khẩu chưa đúng.", "UNAUTHORIZED")
        if not (can_review(user) or user.has_perm("consultation_quality.annotate_quality")):
            raise InputError("Tài khoản chưa được cấp quyền chấm tư vấn.", "FORBIDDEN")
        login(request, user)
    elif request.method == "DELETE":
        logout(request)
    user = request.user
    return JsonResponse({"authenticated": user.is_authenticated, "username": user.get_username() if user.is_authenticated else None,
        "user_id": user.pk if user.is_authenticated else None, "can_review": can_review(user), "csrf_token": get_token(request)})


def rubric_json(row):
    return dict(row.criteria_json, id=str(row.id), version=row.version, status=row.status,
        approved_by=row.approved_by.get_username() if row.approved_by else None,
        approved_at=row.approved_at.isoformat() if row.approved_at else None, approval_note=row.approval_note)


def validate_rubric(data):
    from .rubric import RUBRIC
    version = data.get("version")
    criteria, rules = data.get("criteria"), data.get("general_rules")
    if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", version):
        raise InputError("Mã phiên bản chỉ gồm chữ, số, dấu chấm, gạch nối hoặc gạch dưới.")
    if not isinstance(criteria, list) or len(criteria) != 5 or any(not isinstance(c, dict) for c in criteria):
        raise InputError("Bộ tiêu chí phải có đủ năm mục.")
    if any(not isinstance(c.get("code"), str) for c in criteria) or {c["code"] for c in criteria} != {c["code"] for c in RUBRIC["criteria"]}:
        raise InputError("Không được thay mã năm tiêu chí trong phiên bản này.")
    total = 0
    clean = []
    for c in criteria:
        weight, levels = c.get("weight"), c.get("levels")
        if type(weight) not in (int, float) or not math.isfinite(weight) or not 0 < weight <= 1:
            raise InputError("Trọng số phải lớn hơn 0 và không quá 1.")
        if not isinstance(levels, dict) or set(levels) != {"0", "1", "2"}:
            raise InputError("Mỗi tiêu chí cần định nghĩa đủ mức 0, 1, 2.")
        fields = ["name", "description", "not_assessable", "boundary", "example"]
        if any(not isinstance(v, str) or not v.strip() or len(v) > 5000 for v in [*(c.get(f) for f in fields), *levels.values()]):
            raise InputError("Điền đủ tên, mô tả, mức điểm, ngoại lệ và ví dụ; tối đa 5.000 ký tự mỗi mục.")
        clean.append({"code": c["code"], "weight": weight, "levels": levels, **{f: c[f].strip() for f in fields}})
        total += weight
    if not math.isclose(total, 1, abs_tol=1e-9):
        raise InputError("Tổng trọng số phải bằng 1 (100%).")
    if not isinstance(rules, list) or not 1 <= len(rules) <= 20 or any(not isinstance(x, str) or not x.strip() or len(x) > 5000 for x in rules):
        raise InputError("Cần từ 1 đến 20 quy tắc chấm.")
    return {"version": version, "status": "draft", "criteria": clean, "general_rules": rules}


@endpoint(["GET", "POST"])
def rubrics(request):
    if request.method == "GET":
        return JsonResponse({"rubrics": [rubric_json(r) for r in RubricVersion.objects.order_by("-created_at")]})
    require_reviewer(request)
    data = validate_rubric(body(request))
    with transaction.atomic():
        if RubricVersion.objects.filter(version=data["version"]).exists():
            raise InputError("Mã phiên bản đã tồn tại.", "RUBRIC_LOCKED")
        row = RubricVersion.objects.create(version=data["version"], criteria_json=data)
    return JsonResponse(rubric_json(row), status=201)


@endpoint(["PUT"])
@transaction.atomic
def rubric_detail(request, id):
    require_reviewer(request)
    row = RubricVersion.objects.select_for_update().get(id=id)
    if row.status != "draft" or row.assessments.exists():
        raise InputError("Bộ tiêu chí đã dùng hoặc đã duyệt. Hãy tạo phiên bản mới.", "RUBRIC_LOCKED")
    data = validate_rubric(body(request))
    if data["version"] != row.version:
        raise InputError("Không đổi mã phiên bản khi sửa nháp.")
    row.criteria_json = data
    row.save()
    return JsonResponse(rubric_json(row))


@endpoint(["GET", "PUT"])
@transaction.atomic
def revision_detail(request, id):
    row = Revision.objects.select_for_update().get(id=id, conversation__in=visible_conversations(request.user))
    if request.method == "GET":
        return JsonResponse(revision_json(row))
    if row.status != "draft" or row.assessments.exists():
        raise InputError("Bản đã khóa; tạo revision mới để sửa.", "REVISION_SEALED")
    data = body(request)
    if data.get("expected_content_hash") != row.content_hash:
        raise InputError("Nội dung đã thay đổi; mở lại trước khi lưu.", "REVISION_CONFLICT")
    turns = validate_utterances(data.get("utterances"))
    confirmed, reviewed = data.get("roles_confirmed", False), data.get("transcript_reviewed", False)
    if type(confirmed) is not bool or type(reviewed) is not bool or confirmed and any(t["role"] == "unknown" for t in turns):
        raise InputError("Xác nhận transcript hoặc vai trò không hợp lệ.")
    row.utterances, row.roles_confirmed, row.transcript_reviewed = turns, confirmed, reviewed
    row.save()
    return JsonResponse(revision_json(row))


@endpoint(["POST"])
@transaction.atomic
def seal(request, id):
    row = Revision.objects.select_for_update().get(id=id, conversation__in=visible_conversations(request.user))
    row.status = "sealed"
    row.save()
    return JsonResponse(revision_json(row))


@endpoint(["GET"])
def assessment_detail(request, id):
    row = Assessment.objects.get(id=id, revision__conversation__in=visible_conversations(request.user))
    from .jobs import assessment_visible
    if not assessment_visible(request.user, row):
        raise Assessment.DoesNotExist()
    return JsonResponse(assessment_json(row))


def ensure_assessable(revision):
    if not revision.roles_confirmed or not revision.transcript_reviewed:
        raise InputError("Cần xác nhận nội dung và vai trò người nói.", "ROLES_UNCONFIRMED")
    if AudioSample.objects.filter(conversation=revision.conversation, review_disposition__in=["no_speech", "unclear"]).exists():
        raise InputError("Bản ghi chưa đủ điều kiện chấm.", "AUDIO_NOT_ASSESSABLE")


@endpoint(["POST"])
@transaction.atomic
def approve_assessment(request, id):
    require_reviewer(request)
    row = Assessment.objects.select_for_update().get(id=id)
    if row.source == "model":
        raise InputError("Tạo bản thủ công, kiểm tra điểm và chọn dẫn chứng trước khi duyệt AI.")
    data = body(request)
    rubric = RubricVersion.objects.select_for_update().get(id=row.rubric_version_id)
    if row.status != "needs_review" or rubric.status != "approved":
        raise InputError("Chỉ duyệt bản chờ duyệt dùng rubric đã được chốt.")
    if row.author_id == request.user.id and not PilotResolution.objects.filter(resolved_assessment=row, adjudicator=request.user).exists():
        raise InputError("Không tự duyệt bản chấm độc lập của mình.", "FORBIDDEN")
    if row.supersedes_id and Assessment.objects.filter(supersedes_id=row.supersedes_id, status="approved").exists():
        raise InputError("Bản gốc đã có kết quả thay thế được duyệt.", "REVISION_CONFLICT")
    ensure_assessable(row.revision)
    validate_ratings(row.ratings, row.revision.utterances, rubric=row.rubric)
    note = data.get("note", "")
    if not isinstance(note, str) or not note.strip() or len(note) > 5000:
        raise InputError("Ghi nhận xét trước khi duyệt.")
    row.status, row.reviewer, row.reviewed_at, row.review_note = "approved", request.user, timezone.now(), note.strip()
    row.save()
    return JsonResponse(assessment_json(row))


@endpoint(["GET", "POST"])
@transaction.atomic
def pilot(request):
    require_reviewer(request)
    if request.method == "POST":
        data = body(request)
        ids = data.get("assessment_ids")
        note = data.get("rationale", "")
        if not isinstance(ids, list) or len(ids) != 2 or ids[0] == ids[1] or not isinstance(note, str) or not note.strip() or len(note) > 5000:
            raise InputError("Chọn hai bản chấm độc lập và ghi giải thích thống nhất.")
        a, b = [Assessment.objects.select_for_update().get(id=i) for i in ids]
        if (a.revision_id != b.revision_id or a.rubric_version_id != b.rubric_version_id or
            not a.author_id or not b.author_id or a.author_id == b.author_id or
            a.status != "needs_review" or b.status != "needs_review" or a.source != "manual" or b.source != "manual"):
            raise InputError("Hai người khác nhau phải chấm hoàn tất trên cùng transcript và cùng rubric.")
        if request.user.pk in (a.author_id, b.author_id):
            raise InputError("Người giải quyết bất đồng phải độc lập với hai người chấm.", "FORBIDDEN")
        rubric = RubricVersion.objects.select_for_update().get(pk=a.rubric_version_id)
        if rubric.status != "draft":
            raise InputError("Đợt chốt pilot chỉ nhận rubric nháp.")
        if not AudioSample.objects.filter(conversation=a.revision.conversation, review_disposition__in=["usable", "incomplete"]).exists():
            raise InputError("Pilot phải là audio đã nghe xác nhận có thể chấm hoặc bị cắt có ghi chú.")
        ensure_assessable(a.revision)
        if PilotResolution.objects.filter(revision=a.revision, rubric=rubric).exists():
            raise InputError("Revision này đã có biên bản thống nhất.", "REVISION_CONFLICT")
        rows, total = validate_ratings(data.get("ratings"), a.revision.utterances, rubric=rubric.criteria_json)
        scores_a = {r["criterion_code"]: r["score"] for r in a.ratings}
        scores_b = {r["criterion_code"]: r["score"] for r in b.ratings}
        for r in rows:
            if scores_a[r["criterion_code"]] != scores_b[r["criterion_code"]] and not (r["comment"] or r["not_assessable_reason"]):
                raise InputError("Tiêu chí có bất đồng cần nhận xét giải thích mức kết luận.")
        resolved = Assessment.objects.create(revision=a.revision, rubric=a.rubric, rubric_version=rubric,
            ratings=rows, total_score=total, author=request.user, status="needs_review")
        PilotResolution.objects.create(revision=a.revision, rubric=rubric, assessment_a=a, assessment_b=b,
            resolved_assessment=resolved, adjudicator=request.user, rationale=note.strip())
        return JsonResponse(assessment_json(resolved), status=201)
    rubric_id = request.GET.get("rubric_id")
    rubric = RubricVersion.objects.get(id=rubric_id)
    rows = rubric.pilot_resolutions.select_related("revision__conversation", "assessment_a__author", "assessment_b__author", "adjudicator")
    items = [{"id": str(x.id), "conversation_id": str(x.revision.conversation_id), "title": x.revision.conversation.title,
        "revision_id": str(x.revision_id), "assessment_ids": [str(x.assessment_a_id), str(x.assessment_b_id)],
        "resolved_assessment_id": str(x.resolved_assessment_id), "rationale": x.rationale,
        "annotators": [x.assessment_a.author.get_username(), x.assessment_b.author.get_username()],
        "adjudicator": x.adjudicator.get_username()} for x in rows]
    return JsonResponse({"items": items, "distinct_calls": len({x["conversation_id"] for x in items}), "required_calls": 3})


@endpoint(["POST"])
@transaction.atomic
def approve_rubric(request, id):
    require_reviewer(request)
    row = RubricVersion.objects.select_for_update().get(id=id)
    data = body(request)
    note = data.get("note", "")
    if row.status != "draft" or data.get("confirm_business_rules") is not True or not isinstance(note, str) or not note.strip() or len(note) > 5000:
        raise InputError("Xác nhận tiêu chí, mức điểm, trọng số và ghi kết luận nghiệp vụ trước khi chốt.")
    count = row.pilot_resolutions.values("revision__conversation_id").distinct().count()
    if count < 3:
        raise InputError(f"Mới có {count}/3 cuộc gọi chấm kép đã giải quyết bất đồng. Chưa thể chốt rubric.")
    for resolution in row.pilot_resolutions.select_related("revision"):
        ensure_assessable(resolution.revision)
    row.status, row.approved_by, row.approved_at, row.approval_note = "approved", request.user, timezone.now(), note.strip()
    row.save()
    return JsonResponse(rubric_json(row))
