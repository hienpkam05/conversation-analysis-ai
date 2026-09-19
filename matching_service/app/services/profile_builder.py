from __future__ import annotations

import hashlib
import re
import unicodedata
import uuid
from dataclasses import dataclass
from typing import Iterable

from app.core.enums import EntityStatus
from app.db.models import Campaign, Candidate, Recruiter


@dataclass(frozen=True)
class BuiltProfile:
    text: str
    profile_hash: str


def normalize_profile_text(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip()


def profile_hash(profile_text: str, model_version_id: uuid.UUID) -> str:
    value = f"{normalize_profile_text(profile_text)}|{model_version_id}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_candidate_profile(candidate: Candidate, model_version_id: uuid.UUID) -> BuiltProfile:
    parts = [
        f"Khu vực: {_value_or_unknown(candidate.province)}, {_enum_or_unknown(candidate.region)}.",
        f"Công việc mong muốn: {_value_or_unknown(candidate.desired_job)}.",
        f"Kinh nghiệm: {_value_or_unknown(candidate.experience)}.",
        f"Mức lương kỳ vọng: {_salary_text(candidate.expected_salary)}.",
    ]
    return _built(parts, model_version_id)


def build_recruiter_profile(recruiter: Recruiter, model_version_id: uuid.UUID) -> BuiltProfile:
    region_tags = sorted(
        f"{region.region.value}:{region.province or 'toàn vùng'}" for region in recruiter.regions
    )
    campaign_titles = sorted(
        link.campaign.job_title
        for link in recruiter.campaign_links
        if link.active
        and link.campaign.status == EntityStatus.ACTIVE
        and not link.campaign.is_deleted
    )
    parts = [
        f"Chuyên môn tuyển dụng: {_value_or_unknown(recruiter.specialty)}.",
        f"Khu vực phụ trách: {_list_or_unknown(region_tags)}.",
        f"Chiến dịch đang phụ trách: {_list_or_unknown(campaign_titles)}.",
    ]
    return _built(parts, model_version_id)


def build_campaign_profile(campaign: Campaign, model_version_id: uuid.UUID) -> BuiltProfile:
    parts = [
        f"Vị trí tuyển dụng: {_value_or_unknown(campaign.job_title)}.",
        f"Địa điểm: {_value_or_unknown(campaign.location)}, {_enum_or_unknown(campaign.region)}.",
        f"Yêu cầu: {_value_or_unknown(campaign.requirements)}.",
        f"Phúc lợi: {_value_or_unknown(campaign.benefits)}.",
        f"Khoảng lương: {_salary_range_text(campaign.salary_min, campaign.salary_max)}.",
    ]
    return _built(parts, model_version_id)


def _built(parts: Iterable[str], model_version_id: uuid.UUID) -> BuiltProfile:
    text = normalize_profile_text(" ".join(parts))
    return BuiltProfile(text=text, profile_hash=profile_hash(text, model_version_id))


def _value_or_unknown(value: str | None) -> str:
    return normalize_profile_text(value) if value else "không rõ"


def _enum_or_unknown(value: object | None) -> str:
    raw_value = getattr(value, "value", value)
    return str(raw_value) if raw_value else "không rõ"


def _list_or_unknown(values: list[str]) -> str:
    return ", ".join(values) if values else "không rõ"


def _salary_text(value: int | None) -> str:
    return f"{value:,} VND/tháng" if value is not None else "không rõ"


def _salary_range_text(minimum: int | None, maximum: int | None) -> str:
    if minimum is None and maximum is None:
        return "không rõ"
    if minimum is None:
        return f"đến {maximum:,} VND/tháng"
    if maximum is None:
        return f"từ {minimum:,} VND/tháng"
    return f"{minimum:,} - {maximum:,} VND/tháng"
