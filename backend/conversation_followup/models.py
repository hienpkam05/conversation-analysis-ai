import uuid
from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError


class Summary(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    revision = models.ForeignKey("consultation_quality.Revision", on_delete=models.PROTECT, related_name="summaries")
    revision_hash = models.CharField(max_length=64)
    utterances = models.JSONField()
    sections = models.JSONField()
    metadata = models.JSONField(default=dict)
    source = models.CharField(max_length=20, default="extractive_rules")
    status = models.CharField(max_length=12, default="draft")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="conversation_summaries")
    supersedes = models.ForeignKey("self", null=True, on_delete=models.PROTECT)
    version = models.PositiveIntegerField(default=1)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name="reviewed_summaries")
    reviewed_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        old = type(self).objects.filter(pk=self.pk).first()
        if old:
            if any(getattr(old, f) != getattr(self, f) for f in ("revision_id", "revision_hash", "utterances", "source", "author_id", "supersedes_id")):
                raise ValidationError("Nguồn tóm tắt bất biến; tạo bản mới để thay đổi.")
            if old.source == "extractive_rules" and old.sections != self.sections:
                raise ValidationError("Không ghi đè bản trích dẫn tự động.")
            if old.status == "approved" and any(getattr(old, f) != getattr(self, f) for f in ("sections", "status", "reviewed_by_id", "reviewed_at", "version")):
                raise ValidationError("Tóm tắt đã duyệt không được sửa; tạo bản mới.")
        super().save(*args, **kwargs)


class Appointment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    summary = models.ForeignKey(Summary, on_delete=models.PROTECT, related_name="appointments")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="followup_appointments")
    request_key = models.UUIDField(default=uuid.uuid4)
    title = models.CharField(max_length=200)
    participant = models.CharField(max_length=200, blank=True)
    responsible = models.CharField(max_length=200, blank=True)
    channel = models.CharField(max_length=12, default="phone")
    location = models.CharField(max_length=500, blank=True)
    starts_at = models.DateTimeField(null=True)
    ends_at = models.DateTimeField(null=True)
    evidence_ids = models.JSONField(default=list)
    status = models.CharField(max_length=12, default="draft")
    version = models.PositiveIntegerField(default=1)
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name="confirmed_followups")
    confirmed_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["owner", "request_key"], name="followup_request_key"),
            models.CheckConstraint(condition=models.Q(starts_at__isnull=True, ends_at__isnull=True) | models.Q(starts_at__isnull=False, ends_at__isnull=False, ends_at__gt=models.F("starts_at")), name="followup_time_range")]
        indexes = [models.Index(fields=["owner", "status", "starts_at"], name="followup_schedule")]


class AppointmentEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name="events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=20)
    snapshot = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
