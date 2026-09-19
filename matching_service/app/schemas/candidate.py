import uuid

from pydantic import BaseModel


class CandidateSummary(BaseModel):
    id: uuid.UUID
    province: str | None
    region: str | None
    desired_job: str | None
    experience: str | None
    expected_salary: int | None


class CandidateListResponse(BaseModel):
    candidates: list[CandidateSummary]
