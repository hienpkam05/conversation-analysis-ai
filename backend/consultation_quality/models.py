import uuid
import hashlib
import json

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db import transaction


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="quality_conversations")
    source_reference = models.CharField(max_length=200, blank=True)
    source_type = models.CharField(max_length=10, default="text")

    class Meta:
        permissions = [("annotate_quality", "Can annotate consultation quality"),
                       ("review_quality", "Can review consultation quality")]


class Revision(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="revisions")
    utterances = models.JSONField()
    roles_confirmed = models.BooleanField(default=False)
    transcript_reviewed = models.BooleanField(default=False)
    source_type = models.CharField(max_length=10, default="text")
    created_at = models.DateTimeField(auto_now_add=True)
    revision_number = models.PositiveIntegerField(default=1)
    content_hash = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=10, default="draft")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["conversation", "revision_number"], name="quality_revision_number")]

    def save(self, *args, **kwargs):
        with transaction.atomic():
            Conversation.objects.select_for_update().get(pk=self.conversation_id)
            old = type(self).objects.filter(pk=self.pk).first()
            if old and old.status == "sealed" and any(getattr(old, f) != getattr(self, f) for f in
                    ("utterances", "roles_confirmed", "transcript_reviewed", "source_type", "conversation_id", "revision_number", "status")):
                raise ValidationError("Bản hội thoại đã khóa không được sửa.")
            if not old:
                self.revision_number = (type(self).objects.filter(conversation_id=self.conversation_id)
                    .aggregate(value=models.Max("revision_number"))["value"] or 0) + 1
            self.content_hash = hashlib.sha256(json.dumps({"utterances": self.utterances,
                "roles_confirmed": self.roles_confirmed, "transcript_reviewed": self.transcript_reviewed},
                ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            super().save(*args, **kwargs)
            if not old or old.utterances != self.utterances:
                self.turn_rows.all().delete()
                Utterance.objects.bulk_create([Utterance(revision=self, key=t["id"], position=i,
                    role=t["role"], text=t["text"], start_seconds=t.get("start_seconds"),
                    end_seconds=t.get("end_seconds"), unclear=t.get("unclear", False)) for i, t in enumerate(self.utterances, 1)])


class Utterance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    revision = models.ForeignKey(Revision, on_delete=models.CASCADE, related_name="turn_rows")
    key = models.CharField(max_length=64)
    position = models.PositiveIntegerField()
    role = models.CharField(max_length=12)
    text = models.TextField()
    start_seconds = models.FloatField(null=True)
    end_seconds = models.FloatField(null=True)
    unclear = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["revision", "position"], name="quality_turn_position"),
            models.UniqueConstraint(fields=["revision", "key"], name="quality_turn_key"),
            models.CheckConstraint(condition=models.Q(role__in=["consultant", "candidate", "unknown"]), name="quality_turn_role"),
            models.CheckConstraint(condition=(models.Q(start_seconds__isnull=True, end_seconds__isnull=True) |
                models.Q(start_seconds__gte=0, end_seconds__gt=models.F("start_seconds"), start_seconds__isnull=False, end_seconds__isnull=False)), name="quality_turn_time")]


class RubricVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version = models.CharField(max_length=80, unique=True)
    status = models.CharField(max_length=12, default="draft")
    criteria_json = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    approved_at = models.DateTimeField(null=True)
    approval_note = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        old = type(self).objects.filter(pk=self.pk).first()
        if old and (old.status != "draft" or old.assessments.exists()) and (
                old.criteria_json != self.criteria_json or old.version != self.version):
            raise ValidationError("Tiêu chí đã dùng hoặc đã duyệt phải tạo phiên bản mới.")
        super().save(*args, **kwargs)


class AudioSample(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    call_id = models.CharField(max_length=64, unique=True)
    source_path = models.TextField()
    duration_seconds = models.FloatField()
    conversation = models.OneToOneField(Conversation, on_delete=models.PROTECT, related_name="audio_sample")
    status = models.CharField(max_length=20, default="pending")
    model_version = models.CharField(max_length=200, blank=True)
    error_code = models.CharField(max_length=100, blank=True)
    transcript_metadata = models.JSONField(default=dict)
    review_disposition = models.CharField(max_length=20, default="unreviewed")
    review_note = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class Assessment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    revision = models.ForeignKey(Revision, on_delete=models.CASCADE, related_name="assessments")
    rubric = models.JSONField()
    ratings = models.JSONField()
    total_score = models.FloatField(null=True)
    source = models.CharField(max_length=10, default="manual")
    status = models.CharField(max_length=20, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)
    rubric_version = models.ForeignKey(RubricVersion, null=True, on_delete=models.PROTECT, related_name="assessments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name="quality_assessments")
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name="quality_reviews")
    reviewed_at = models.DateTimeField(null=True)
    review_note = models.TextField(blank=True)
    model_version = models.CharField(max_length=200, blank=True)
    preprocessing_version = models.CharField(max_length=100, blank=True)
    supersedes = models.ForeignKey("self", null=True, on_delete=models.PROTECT)
    inference_metadata = models.JSONField(default=dict)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(total_score__isnull=True) |
            models.Q(total_score__gte=0, total_score__lte=100), name="quality_total_range")]

    def save(self, *args, **kwargs):
        with transaction.atomic():
            old = type(self).objects.filter(pk=self.pk).first()
            if old and any(getattr(old, f) != getattr(self, f) for f in
                    ("revision_id", "rubric", "ratings", "total_score", "source", "author_id", "rubric_version_id", "supersedes_id", "inference_metadata", "model_version", "preprocessing_version")):
                raise ValidationError("Bản chấm là snapshot bất biến; hãy tạo bản thay thế.")
            if not self.rubric_version_id:
                self.rubric_version, _ = RubricVersion.objects.get_or_create(version=self.rubric["version"],
                    defaults={"criteria_json": self.rubric})
            super().save(*args, **kwargs)
            if not old:
                Revision.objects.filter(pk=self.revision_id).update(status="sealed")
                for r in self.ratings:
                    row = CriterionRating.objects.create(assessment=self, criterion_code=r["criterion_code"],
                        score=r["score"], comment=r.get("comment", ""), not_assessable_reason=r.get("not_assessable_reason", ""))
                    e = r.get("evidence", {})
                    Evidence.objects.create(rating=row, kind=e.get("kind", "quote"),
                        utterance_ids=e.get("utterance_ids", []), explanation=e.get("explanation", r.get("comment", "")))
                    if self.source == "model":
                        row.confidence = self.inference_metadata.get("confidence", {}).get(r["criterion_code"])
                        row.save(update_fields=["confidence"])


class CriterionRating(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="rating_rows")
    criterion_code = models.CharField(max_length=80)
    score = models.PositiveSmallIntegerField(null=True)
    confidence = models.FloatField(null=True)
    comment = models.TextField(blank=True)
    not_assessable_reason = models.TextField(blank=True)
    review_required = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["assessment", "criterion_code"], name="quality_rating_code"),
            models.CheckConstraint(condition=models.Q(score__isnull=True) | models.Q(score__in=[0, 1, 2]), name="quality_score_range"),
            models.CheckConstraint(condition=models.Q(confidence__isnull=True) | models.Q(confidence__gte=0, confidence__lte=1), name="quality_confidence_range")]


class Evidence(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rating = models.OneToOneField(CriterionRating, on_delete=models.CASCADE, related_name="evidence_row")
    kind = models.CharField(max_length=10)
    utterance_ids = models.JSONField(default=list)
    explanation = models.TextField(blank=True)


class PilotResolution(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    revision = models.ForeignKey(Revision, on_delete=models.PROTECT)
    rubric = models.ForeignKey(RubricVersion, on_delete=models.PROTECT, related_name="pilot_resolutions")
    assessment_a = models.ForeignKey(Assessment, on_delete=models.PROTECT, related_name="pilot_a")
    assessment_b = models.ForeignKey(Assessment, on_delete=models.PROTECT, related_name="pilot_b")
    resolved_assessment = models.OneToOneField(Assessment, on_delete=models.PROTECT, related_name="resolution")
    adjudicator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    rationale = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["revision", "rubric"], name="quality_pilot_resolution")]


class AssessmentJob(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    revision = models.ForeignKey(Revision, on_delete=models.PROTECT, related_name="assessment_jobs")
    rubric = models.ForeignKey(RubricVersion, on_delete=models.PROTECT)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    request_key = models.UUIDField(default=uuid.uuid4)
    model_version = models.CharField(max_length=200)
    preprocessing_version = models.CharField(max_length=100)
    manifest_hash = models.CharField(max_length=64)
    revision_hash = models.CharField(max_length=64)
    rubric_hash = models.CharField(max_length=64)
    status = models.CharField(max_length=12, default="queued")
    assessment = models.OneToOneField(Assessment, null=True, on_delete=models.PROTECT, related_name="ai_job")
    error_code = models.CharField(max_length=80, blank=True)
    completed_windows = models.PositiveIntegerField(default=0)
    total_windows = models.PositiveIntegerField(default=0)
    worker_token = models.UUIDField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True)
    finished_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["requested_by", "request_key"], name="quality_job_request_key"),
            models.CheckConstraint(condition=models.Q(status__in=["queued", "running", "succeeded", "failed"]), name="quality_job_status")]
        indexes = [models.Index(fields=["status", "created_at"], name="quality_job_queue")]


class QualityWorkerSlot(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    token = models.UUIDField(null=True)
    lease_until = models.DateTimeField(null=True)
    last_seen = models.DateTimeField(null=True)
