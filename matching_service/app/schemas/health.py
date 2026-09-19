from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str = "candidate-recruiter-matching"
    postgres: str
    qdrant: str
    detail: str | None = None
