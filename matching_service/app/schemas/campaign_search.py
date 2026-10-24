import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.core.enums import Region


class CampaignSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    desired_job: str = Field(min_length=1, max_length=500)
    experience: str | None = Field(default=None, max_length=1000)
    desired_location: str | None = Field(default=None, max_length=300)
    region: Region | None = None
    expected_salary: int | None = Field(default=None, strict=True, gt=0, le=1_000_000_000)
    strict_salary: bool = Field(default=False, strict=True)
    shift: Literal["day", "night", "rotating"] | None = None
    top_k: int = Field(default=3, strict=True, ge=1, le=10)

    @model_validator(mode="after")
    def salary_filter_requires_value(self):
        if self.strict_salary and self.expected_salary is None:
            raise ValueError("Cần mức lương mong muốn khi bật lọc cứng.")
        return self


class CampaignRecommendation(BaseModel):
    campaign_id: uuid.UUID
    job_title: str
    location: str | None
    region: Region | None
    salary_min: int | None
    salary_max: int | None
    requirements: str | None
    benefits: str | None
    status: Literal["active"] = "active"
    semantic_score: float = Field(ge=-1, le=1)
    warnings: list[str]


class CampaignSearchResponse(BaseModel):
    model_version_id: uuid.UUID | None = None
    model_name: str | None = None
    eligible_campaigns: int
    indexed_campaigns: int
    recommendations: list[CampaignRecommendation]
    message: str | None = None
