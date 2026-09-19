import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import EmbeddingProviderUnavailable
from app.db.session import get_db_session
from app.schemas.matching import MatchRequest, MatchingResponse, Recommendation
from app.services.hard_filter_service import CandidateNotFoundError, CandidateRegionRequiredError
from app.services.matching_service import (
    ActiveModelVersionNotFoundError,
    MatchingService,
    ModelVersionConfigurationError,
)
from app.services.qdrant_service import VectorStoreUnavailableError

router = APIRouter(prefix="/matching", tags=["matching"])


@router.post("/candidates/{candidate_id}", response_model=MatchingResponse)
async def match_candidate(
    candidate_id: uuid.UUID,
    request: MatchRequest,
    session: AsyncSession = Depends(get_db_session),
) -> MatchingResponse:
    try:
        result = await MatchingService(session).match(candidate_id, request.top_k)
    except CandidateNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "CANDIDATE_NOT_FOUND", "message": "Không tìm thấy ứng viên."}) from exc
    except CandidateRegionRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"code": "CANDIDATE_REGION_REQUIRED", "message": "Ứng viên chưa có vùng để matching."}) from exc
    except EmbeddingProviderUnavailable as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"code": "EMBEDDING_MODEL_UNAVAILABLE", "message": str(exc)}) from exc
    except VectorStoreUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"code": "VECTOR_STORE_UNAVAILABLE", "message": str(exc)}) from exc
    except (ActiveModelVersionNotFoundError, ModelVersionConfigurationError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": "EMBEDDING_CONFIGURATION_INVALID", "message": str(exc)}) from exc

    recommendations = [
        Recommendation(
            rank=index,
            recruiter_id=item.recruiter.id,
            specialty=item.recruiter.specialty,
            active_campaigns=item.active_campaigns,
            current_workload=item.recruiter.current_workload,
            max_workload=item.recruiter.max_workload,
            final_score=item.final_score,
            semantic_score=item.semantic_score,
            campaign_fit_score=item.campaign_fit_score,
            performance_score=item.performance_score,
            workload_score=item.workload_score,
            reasons=item.reasons,
        )
        for index, item in enumerate(result.recommendations, start=1)
    ]
    return MatchingResponse(
        candidate_id=result.candidate_id,
        eligible_recruiters=result.eligible_recruiters,
        retrieved_recruiters=result.retrieved_recruiters,
        top_k=len(recommendations),
        recommendations=recommendations,
        message="Không có recruiter đủ điều kiện." if result.eligible_recruiters == 0 else None,
    )
