from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any, Iterable

from qdrant_client import AsyncQdrantClient, models

from app.core.config import Settings, get_settings


class VectorStoreUnavailableError(RuntimeError):
    pass


class VectorDimensionMismatchError(RuntimeError):
    pass


@dataclass(frozen=True)
class VectorHit:
    point_id: uuid.UUID
    score: float
    payload: dict[str, Any]


def collection_name(object_type: str, model_name: str, model_version: str) -> str:
    model_key = re.sub(r"[^a-z0-9]+", "_", f"{model_name}_{model_version}".lower()).strip("_")
    return f"{object_type}_embeddings__{model_key}"


class QdrantService:
    def __init__(self, *, settings: Settings | None = None, client: AsyncQdrantClient | None = None):
        self.settings = settings or get_settings()
        self.client = client or AsyncQdrantClient(
            url=self.settings.qdrant_url,
            api_key=self.settings.qdrant_api_key,
        )

    async def ensure_collection(self, name: str, dimension: int, payload_fields: Iterable[str]) -> bool:
        """Tra ve True neu collection vua duoc tao."""
        try:
            exists = await self.client.collection_exists(name)
            if exists:
                info = await self.client.get_collection(name)
                current_dimension = _collection_dimension(info)
                if current_dimension != dimension:
                    raise VectorDimensionMismatchError(
                        f"Collection '{name}' co dimension {current_dimension}, khac dimension provider {dimension}."
                    )
                return False

            await self.client.create_collection(
                collection_name=name,
                vectors_config=models.VectorParams(size=dimension, distance=models.Distance.COSINE),
            )
            for field in payload_fields:
                await self.client.create_payload_index(
                    collection_name=name,
                    field_name=field,
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )
            return True
        except VectorDimensionMismatchError:
            raise
        except Exception as exc:
            raise VectorStoreUnavailableError(f"Qdrant khong san sang: {exc}") from exc

    async def upsert(self, name: str, points: list[models.PointStruct]) -> None:
        if not points:
            return
        try:
            await self.client.upsert(collection_name=name, points=points, wait=True)
        except Exception as exc:
            raise VectorStoreUnavailableError(f"Khong the ghi vector vao Qdrant: {exc}") from exc

    async def query_recruiters(
        self,
        *,
        name: str,
        vector: list[float],
        eligible_recruiter_ids: list[uuid.UUID],
        model_version_id: uuid.UUID,
        limit: int,
    ) -> list[VectorHit]:
        if not eligible_recruiter_ids:
            return []
        return await self.query_by_ids(
            name=name,
            vector=vector,
            id_field="recruiter_id",
            object_ids=eligible_recruiter_ids,
            model_version_id=model_version_id,
            limit=limit,
        )

    async def query_campaigns(
        self,
        *,
        name: str,
        vector: list[float],
        campaign_ids: list[uuid.UUID],
        model_version_id: uuid.UUID,
        limit: int,
    ) -> list[VectorHit]:
        return await self.query_by_ids(
            name=name,
            vector=vector,
            id_field="campaign_id",
            object_ids=campaign_ids,
            model_version_id=model_version_id,
            limit=limit,
        )

    async def query_by_ids(
        self,
        *,
        name: str,
        vector: list[float],
        id_field: str,
        object_ids: list[uuid.UUID],
        model_version_id: uuid.UUID,
        limit: int,
    ) -> list[VectorHit]:
        if not object_ids:
            return []
        query_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key=id_field,
                    match=models.MatchAny(any=[str(value) for value in object_ids]),
                ),
                models.FieldCondition(
                    key="model_version_id",
                    match=models.MatchValue(value=str(model_version_id)),
                ),
            ]
        )
        try:
            response = await self.client.query_points(
                collection_name=name,
                query=vector,
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
            )
        except Exception as exc:
            raise VectorStoreUnavailableError(f"Khong the truy van Qdrant: {exc}") from exc
        return [
            VectorHit(point_id=uuid.UUID(str(point.id)), score=float(point.score), payload=dict(point.payload or {}))
            for point in response.points
        ]

    async def close(self) -> None:
        await self.client.close()


def _collection_dimension(info: models.CollectionInfo) -> int:
    vectors = info.config.params.vectors
    if isinstance(vectors, models.VectorParams):
        return vectors.size
    if isinstance(vectors, dict) and vectors:
        first_vector = next(iter(vectors.values()))
        return first_vector.size
    raise VectorDimensionMismatchError("Khong doc duoc dimension cua collection Qdrant.")
