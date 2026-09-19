import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Candidate


class CandidateRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active_by_id(self, candidate_id: uuid.UUID) -> Candidate | None:
        statement = select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.is_deleted.is_(False),
        )
        return await self.session.scalar(statement)

    async def list_active(self) -> list[Candidate]:
        statement = (
            select(Candidate)
            .where(Candidate.is_deleted.is_(False))
            .order_by(Candidate.created_at.desc(), Candidate.id)
        )
        return list((await self.session.scalars(statement)).all())
