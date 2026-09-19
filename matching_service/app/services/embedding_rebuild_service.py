from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from qdrant_client import models
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import EmbeddingProvider, get_embedding_provider
from app.core.config import Settings, get_settings
from app.db.models import Campaign, ModelVersion, Recruiter
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.embedding_ref_repository import EmbeddingRefRepository
from app.repositories.model_version_repository import ModelVersionRepository
from app.repositories.recruiter_repository import RecruiterRepository
from app.services.profile_builder import BuiltProfile, build_campaign_profile, build_recruiter_profile
from app.services.qdrant_service import QdrantService, collection_name


class ActiveModelVersionNotFoundError(RuntimeError):
    pass


class ModelVersionConfigurationError(RuntimeError):
    pass


T = TypeVar("T", Recruiter, Campaign)


@dataclass(frozen=True)
class RebuildResult:
    object_type: str
    collection_name: str
    model_version_id: uuid.UUID
    total: int
    embedded: int
    skipped: int


@dataclass(frozen=True)
class ProfileRecord(Generic[T]):
    obj: T
    profile: BuiltProfile
    payload: dict[str, Any]


class EmbeddingRebuildService:
    embedding_type = "semantic_profile"
    model_task = "recruiter_matching_embedding"

    def __init__(
        self,
        session: AsyncSession,
        *,
        settings: Settings | None = None,
        provider: EmbeddingProvider | None = None,
        qdrant: QdrantService | None = None,
    ):
        self.session = session
        self.settings = settings or get_settings()
        self.provider = provider or get_embedding_provider()
        self.qdrant = qdrant or QdrantService(settings=self.settings)
        self.models = ModelVersionRepository(session)
        self.refs = EmbeddingRefRepository(session)
        self.recruiters = RecruiterRepository(session)
        self.campaigns = CampaignRepository(session)

    async def rebuild_recruiters(self) -> RebuildResult:
        model_version = await self._active_model_version()
        recruiters = await self.recruiters.find_active_for_embedding()
        records = [
            ProfileRecord(
                obj=recruiter,
                profile=build_recruiter_profile(recruiter, model_version.id),
                payload={
                    "recruiter_id": str(recruiter.id),
                    "model_version_id": str(model_version.id),
                    "region_tags": sorted(
                        f"{region.region.value}:{region.province or '*'}" for region in recruiter.regions
                    ),
                },
            )
            for recruiter in recruiters
        ]
        return await self._rebuild("recruiter", model_version, records, ["recruiter_id", "model_version_id", "region_tags"])

    async def rebuild_campaigns(self) -> RebuildResult:
        model_version = await self._active_model_version()
        campaigns = await self.campaigns.find_active_for_embedding()
        records = [
            ProfileRecord(
                obj=campaign,
                profile=build_campaign_profile(campaign, model_version.id),
                payload={
                    "campaign_id": str(campaign.id),
                    "model_version_id": str(model_version.id),
                    "status": campaign.status.value,
                    "location_tags": [value for value in (campaign.region.value if campaign.region else None, campaign.location) if value],
                },
            )
            for campaign in campaigns
        ]
        return await self._rebuild("campaign", model_version, records, ["campaign_id", "model_version_id", "status", "location_tags"])

    async def _active_model_version(self) -> ModelVersion:
        model_version = await self.models.get_active_for_task(self.model_task)
        if model_version is None:
            raise ActiveModelVersionNotFoundError("Khong tim thay model version active cho embedding.")
        if (
            model_version.model_name != self.settings.embedding_model
            or model_version.version != self.settings.embedding_model_version
        ):
            raise ModelVersionConfigurationError(
                "Cau hinh EMBEDDING_MODEL khong khop model version active. "
                "Hay dang ky model version va rebuild collection truoc khi switch config."
            )
        return model_version

    async def _rebuild(
        self,
        object_type: str,
        model_version: ModelVersion,
        records: list[ProfileRecord[Any]],
        payload_fields: list[str],
    ) -> RebuildResult:
        name = collection_name(object_type, model_version.model_name, model_version.version)
        collection_created = await self.qdrant.ensure_collection(name, self.provider.dimension, payload_fields)
        refs = await self.refs.find_for_objects(
            object_type=object_type,
            object_ids=[record.obj.id for record in records],
            model_version_id=model_version.id,
            embedding_type=self.embedding_type,
        )
        stale_records = [
            record
            for record in records
            if collection_created
            or record.obj.id not in refs
            or refs[record.obj.id].profile_hash != record.profile.profile_hash
            or refs[record.obj.id].qdrant_collection != name
        ]
        if stale_records:
            vectors = self.provider.encode([record.profile.text for record in stale_records])
            points = [
                models.PointStruct(
                    id=self._point_id(object_type, model_version.id, record.obj.id),
                    vector=vector.tolist(),
                    payload={**record.payload, "profile_hash": record.profile.profile_hash},
                )
                for record, vector in zip(stale_records, vectors, strict=True)
            ]
            await self.qdrant.upsert(name, points)
            for record, point in zip(stale_records, points, strict=True):
                await self.refs.upsert(
                    object_type=object_type,
                    object_id=record.obj.id,
                    model_version_id=model_version.id,
                    embedding_type=self.embedding_type,
                    qdrant_collection=name,
                    point_id=uuid.UUID(str(point.id)),
                    profile_hash=record.profile.profile_hash,
                )
            await self.session.commit()
        return RebuildResult(
            object_type=object_type,
            collection_name=name,
            model_version_id=model_version.id,
            total=len(records),
            embedded=len(stale_records),
            skipped=len(records) - len(stale_records),
        )

    @staticmethod
    def _point_id(object_type: str, model_version_id: uuid.UUID, object_id: uuid.UUID) -> uuid.UUID:
        return uuid.uuid5(uuid.NAMESPACE_URL, f"candidate-recruiter-matching/{object_type}/{model_version_id}/{object_id}")
