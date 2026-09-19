import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EmbeddingRef


class EmbeddingRefRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_for_objects(
        self,
        *,
        object_type: str,
        object_ids: list[uuid.UUID],
        model_version_id: uuid.UUID,
        embedding_type: str,
    ) -> dict[uuid.UUID, EmbeddingRef]:
        if not object_ids:
            return {}
        statement = select(EmbeddingRef).where(
            EmbeddingRef.object_type == object_type,
            EmbeddingRef.object_id.in_(object_ids),
            EmbeddingRef.model_version_id == model_version_id,
            EmbeddingRef.embedding_type == embedding_type,
        )
        refs = (await self.session.scalars(statement)).all()
        return {ref.object_id: ref for ref in refs}

    async def upsert(
        self,
        *,
        object_type: str,
        object_id: uuid.UUID,
        model_version_id: uuid.UUID,
        embedding_type: str,
        qdrant_collection: str,
        point_id: uuid.UUID,
        profile_hash: str,
    ) -> None:
        statement = insert(EmbeddingRef).values(
            object_type=object_type,
            object_id=object_id,
            model_version_id=model_version_id,
            embedding_type=embedding_type,
            qdrant_collection=qdrant_collection,
            point_id=point_id,
            profile_hash=profile_hash,
        )
        statement = statement.on_conflict_do_update(
            index_elements=["object_type", "object_id", "model_version_id", "embedding_type"],
            set_={
                "qdrant_collection": statement.excluded.qdrant_collection,
                "point_id": statement.excluded.point_id,
                "profile_hash": statement.excluded.profile_hash,
            },
        )
        await self.session.execute(statement)
