import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class CandidateProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    revision = models.ForeignKey("consultation_quality.Revision", on_delete=models.PROTECT, related_name="candidate_profiles")
    revision_hash = models.CharField(max_length=64)
    utterances = models.JSONField()
    fields = models.JSONField()
    source = models.CharField(max_length=10)
    status = models.CharField(max_length=12, default="draft")
    version = models.PositiveIntegerField(default=1)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="candidate_profiles")
    supersedes = models.ForeignKey("self", on_delete=models.PROTECT, null=True)
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, related_name="confirmed_candidate_profiles")
    confirmed_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(source__in=["rules", "manual"]), name="candidate_info_source"),
            models.CheckConstraint(condition=(models.Q(status="draft", confirmed_by__isnull=True, confirmed_at__isnull=True) | models.Q(status="confirmed", confirmed_by__isnull=False, confirmed_at__isnull=False)), name="candidate_info_confirmation")]

    def save(self, *args, **kwargs):
        old = type(self).objects.filter(pk=self.pk).first()
        if old:
            frozen = ("revision_id", "revision_hash", "utterances", "fields", "source", "author_id", "supersedes_id")
            if any(getattr(old, key) != getattr(self, key) for key in frozen):
                raise ValidationError("Bản thông tin bất biến; tạo bản sửa riêng.")
            if old.status == "confirmed" and any(getattr(old, key) != getattr(self, key) for key in ("status", "version", "confirmed_by_id", "confirmed_at")):
                raise ValidationError("Không thay đổi bản đã xác nhận.")
        super().save(*args, **kwargs)


class CampaignSearch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(CandidateProfile, on_delete=models.PROTECT, related_name="searches")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    query = models.JSONField()
    result = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Kết quả tìm kiếm là snapshot bất biến.")
        super().save(*args, **kwargs)
