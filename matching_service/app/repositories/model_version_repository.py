from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ModelVersion


class ModelVersionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active_for_task(self, task: str) -> ModelVersion | None:
        statement = (
            select(ModelVersion)
            .where(ModelVersion.task == task, ModelVersion.is_active.is_(True))
            .order_by(ModelVersion.deployed_at.desc())
        )
        return await self.session.scalar(statement)
