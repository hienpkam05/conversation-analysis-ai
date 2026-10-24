import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class StatusDecision(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    revision = models.ForeignKey("consultation_quality.Revision", on_delete=models.PROTECT, related_name="status_decisions")
    revision_hash = models.CharField(max_length=64)
    utterances = models.JSONField()
    taxonomy_version = models.CharField(max_length=80, default="candidate-status-draft-v1")
    taxonomy_hash = models.CharField(max_length=64, blank=True)
    source = models.CharField(max_length=10)
    label = models.CharField(max_length=32)
    evidence_ids = models.JSONField(default=list)
    rationale = models.TextField()
    metadata = models.JSONField(default=dict)
    status = models.CharField(max_length=12, default="draft")
    version = models.PositiveIntegerField(default=1)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="status_decisions")
    supersedes = models.ForeignKey("self", null=True, on_delete=models.PROTECT)
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name="confirmed_status_decisions")
    confirmed_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(source__in=["rules", "manual", "model"]), name="candidate_status_source"),
            models.CheckConstraint(condition=models.Q(label__in=["interested", "needs_information", "callback_requested", "interview_agreed", "declined", "unknown"]), name="candidate_status_label"),
            models.CheckConstraint(condition=(models.Q(status="draft", confirmed_by__isnull=True, confirmed_at__isnull=True) | models.Q(status="confirmed", confirmed_by__isnull=False, confirmed_at__isnull=False)), name="candidate_status_confirmation"),
        ]

    def save(self, *args, **kwargs):
        old = type(self).objects.filter(pk=self.pk).first()
        if old:
            frozen = ("revision_id", "revision_hash", "utterances", "taxonomy_version", "taxonomy_hash", "source", "label", "evidence_ids", "rationale", "metadata", "author_id", "supersedes_id")
            if any(getattr(old, key) != getattr(self, key) for key in frozen):
                raise ValidationError("Bản phân loại bất biến; tạo bản sửa thủ công mới.")
            if old.status == "confirmed" and any(getattr(old, key) != getattr(self, key) for key in ("status", "version", "confirmed_by_id", "confirmed_at")):
                raise ValidationError("Không sửa bản đã xác nhận.")
        super().save(*args, **kwargs)


class TaxonomyApproval(models.Model):
    version = models.CharField(max_length=80, unique=True)
    definition_hash = models.CharField(max_length=64)
    definitions = models.JSONField()
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Phê duyệt bộ nhãn bất biến; thay định nghĩa cần phiên bản mới.")
        super().save(*args, **kwargs)


class LabelReview(models.Model):
    decision = models.OneToOneField(StatusDecision, on_delete=models.PROTECT, related_name="training_review")
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    verdict = models.CharField(max_length=10, choices=[("approved", "approved"), ("rejected", "rejected")])
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Kết quả duyệt nhãn bất biến; tạo bản sửa mới để duyệt lại.")
        super().save(*args, **kwargs)
