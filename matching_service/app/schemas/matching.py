import uuid

from pydantic import BaseModel, Field


class MatchRequest(BaseModel):
    top_k: int = Field(default=3, ge=1, le=20)


class Recommendation(BaseModel):
    rank: int
    recruiter_id: uuid.UUID
    specialty: str | None
    active_campaigns: list[str]
    current_workload: int
    max_workload: int
    final_score: float
    semantic_score: float
    campaign_fit_score: float
    performance_score: float
    workload_score: float
    reasons: list[str]


class MatchingResponse(BaseModel):
    candidate_id: uuid.UUID
    eligible_recruiters: int
    retrieved_recruiters: int
    top_k: int
    recommendations: list[Recommendation]
    message: str | None = None
