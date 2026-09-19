import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db_session
from app.schemas.eligibility import EligibleRecruiter, EligibleRecruitersResponse
from app.services.hard_filter_service import (
    CandidateNotFoundError,
    CandidateRegionRequiredError,
    HardFilterService,
)

router = APIRouter(tags=["hard-filter"])


@router.get(
    "/candidates/{candidate_id}/eligible-recruiters",
    response_model=EligibleRecruitersResponse,
)
async def eligible_recruiters(
    candidate_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> EligibleRecruitersResponse:
    settings = get_settings()
    service = HardFilterService(session, settings=settings)
    try:
        result = await service.eligible_recruiters(candidate_id)
    except CandidateNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CANDIDATE_NOT_FOUND", "message": "Không tìm thấy ứng viên."},
        ) from exc
    except CandidateRegionRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "CANDIDATE_REGION_REQUIRED", "message": "Ứng viên chưa có region để lọc cứng."},
        ) from exc

    items = []
    for recruiter in result.recruiters:
        active_campaigns = sorted(
            link.campaign.job_title
            for link in recruiter.campaign_links
            if link.active and link.campaign.status.value == "active" and not link.campaign.is_deleted
        )
        regions = sorted(
            f"{region.region.value}:{region.province or '*'}" for region in recruiter.regions
        )
        items.append(
            EligibleRecruiter(
                recruiter_id=recruiter.id,
                specialty=recruiter.specialty,
                current_workload=recruiter.current_workload,
                max_workload=recruiter.max_workload,
                regions=regions,
                active_campaigns=active_campaigns,
            )
        )

    return EligibleRecruitersResponse(
        candidate_id=result.candidate.id,
        total=len(items),
        strict_region=settings.strict_region,
        require_active_campaign=settings.require_active_campaign,
        recruiters=items,
    )
