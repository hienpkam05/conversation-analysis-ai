from collections.abc import Sequence

from sqlalchemy import exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import EntityStatus
from app.db.models import Campaign, Candidate, Recruiter, RecruiterCampaign, RecruiterRegion


class RecruiterRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_eligible(
        self,
        candidate: Candidate,
        *,
        strict_region: bool,
        require_active_campaign: bool,
    ) -> Sequence[Recruiter]:
        statement = (
            select(Recruiter)
            .where(
                Recruiter.status == EntityStatus.ACTIVE,
                Recruiter.is_deleted.is_(False),
                Recruiter.current_workload < Recruiter.max_workload,
            )
            .options(
                selectinload(Recruiter.regions),
                selectinload(Recruiter.campaign_links).selectinload(RecruiterCampaign.campaign),
            )
            .order_by(Recruiter.id)
        )

        if strict_region:
            region_scope = select(RecruiterRegion.recruiter_id).where(
                RecruiterRegion.region == candidate.region
            )
            if candidate.province:
                region_scope = region_scope.where(
                    or_(
                        RecruiterRegion.province.is_(None),
                        RecruiterRegion.province == candidate.province,
                    )
                )
            statement = statement.where(Recruiter.id.in_(region_scope))

        if require_active_campaign:
            active_campaign_exists = exists(
                select(1)
                .select_from(RecruiterCampaign)
                .join(Campaign, Campaign.id == RecruiterCampaign.campaign_id)
                .where(
                    RecruiterCampaign.recruiter_id == Recruiter.id,
                    RecruiterCampaign.active.is_(True),
                    Campaign.status == EntityStatus.ACTIVE,
                    Campaign.is_deleted.is_(False),
                )
            )
            statement = statement.where(active_campaign_exists)

        return (await self.session.scalars(statement)).all()

    async def find_active_for_embedding(self) -> list[Recruiter]:
        statement = (
            select(Recruiter)
            .options(
                selectinload(Recruiter.regions),
                selectinload(Recruiter.campaign_links).selectinload(RecruiterCampaign.campaign),
            )
            .where(Recruiter.status == EntityStatus.ACTIVE, Recruiter.is_deleted.is_(False))
            .order_by(Recruiter.id)
        )
        return list((await self.session.scalars(statement)).all())
