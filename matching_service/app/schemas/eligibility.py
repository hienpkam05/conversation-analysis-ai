import uuid

from pydantic import BaseModel


class EligibleRecruiter(BaseModel):
    recruiter_id: uuid.UUID
    specialty: str | None
    current_workload: int
    max_workload: int
    regions: list[str]
    active_campaigns: list[str]


class EligibleRecruitersResponse(BaseModel):
    candidate_id: uuid.UUID
    total: int
    strict_region: bool
    require_active_campaign: bool
    recruiters: list[EligibleRecruiter]
