from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.repositories.candidate_repository import CandidateRepository
from app.schemas.candidate import CandidateListResponse, CandidateSummary

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get("", response_model=CandidateListResponse)
async def list_candidates(session: AsyncSession = Depends(get_db_session)) -> CandidateListResponse:
    candidates = await CandidateRepository(session).list_active()
    return CandidateListResponse(
        candidates=[
            CandidateSummary(
                id=candidate.id,
                province=candidate.province,
                region=candidate.region.value if candidate.region else None,
                desired_job=candidate.desired_job,
                experience=candidate.experience,
                expected_salary=candidate.expected_salary,
            )
            for candidate in candidates
        ]
    )
