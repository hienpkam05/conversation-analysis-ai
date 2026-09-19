import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import EntityStatus
from app.db.models import Campaign, RecruiterCampaign


class CampaignRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_active_for_recruiters(
        self, recruiter_ids: Sequence[uuid.UUID]
    ) -> Sequence[RecruiterCampaign]:
        if not recruiter_ids:
            return []

        statement = (
            select(RecruiterCampaign)
            .join(Campaign, Campaign.id == RecruiterCampaign.campaign_id)
            .where(
                RecruiterCampaign.recruiter_id.in_(recruiter_ids),
                RecruiterCampaign.active.is_(True),
                Campaign.status == EntityStatus.ACTIVE,
                Campaign.is_deleted.is_(False),
            )
            .options(selectinload(RecruiterCampaign.campaign))
        )
        return (await self.session.scalars(statement)).all()

    async def find_active_for_embedding(self) -> list[Campaign]:
        statement = (
            select(Campaign)
            .where(Campaign.status == EntityStatus.ACTIVE, Campaign.is_deleted.is_(False))
            .order_by(Campaign.id)
        )
        return list((await self.session.scalars(statement)).all())
