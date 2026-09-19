from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal

from app.ai.providers import EmbeddingProvider, get_embedding_provider
from app.core.config import Settings, get_settings
from app.core.enums import EntityStatus
from app.db.models import ModelVersion, Recruiter
from app.repositories.model_version_repository import ModelVersionRepository
from app.services.hard_filter_service import HardFilterService
from app.services.profile_builder import build_candidate_profile
from app.services.qdrant_service import QdrantService, VectorHit, collection_name


class ActiveModelVersionNotFoundError(RuntimeError):
    pass


class ModelVersionConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class ScoredRecommendation:
    recruiter: Recruiter
    active_campaigns: list[str]
    semantic_score: float
    campaign_fit_score: float
    performance_score: float
    workload_score: float
    final_score: float
    reasons: list[str]


@dataclass(frozen=True)
class MatchingResult:
    candidate_id: uuid.UUID
    eligible_recruiters: int
    retrieved_recruiters: int
    recommendations: list[ScoredRecommendation]


class MatchingService:
    model_task = "recruiter_matching_embedding"

    def __init__(
        self,
        session,
        *,
        settings: Settings | None = None,
        provider: EmbeddingProvider | None = None,
        qdrant: QdrantService | None = None,
        hard_filter: HardFilterService | None = None,
        model_versions: ModelVersionRepository | None = None,
    ):
        self.settings = settings or get_settings()
        self.provider = provider or get_embedding_provider()
        self.qdrant = qdrant or QdrantService(settings=self.settings)
        self.hard_filter = hard_filter or HardFilterService(session, settings=self.settings)
        self.model_versions = model_versions or ModelVersionRepository(session)

    async def match(self, candidate_id: uuid.UUID, requested_top_k: int) -> MatchingResult:
        filtered = await self.hard_filter.eligible_recruiters(candidate_id)
        if not filtered.recruiters:
            return MatchingResult(candidate_id=candidate_id, eligible_recruiters=0, retrieved_recruiters=0, recommendations=[])

        model_version = await self._active_model_version()
        candidate_profile = build_candidate_profile(filtered.candidate, model_version.id)
        candidate_vector = self.provider.encode_one(candidate_profile.text)
        recruiter_collection = collection_name("recruiter", model_version.model_name, model_version.version)
        recruiter_hits = await self.qdrant.query_recruiters(
            name=recruiter_collection,
            vector=candidate_vector,
            eligible_recruiter_ids=[recruiter.id for recruiter in filtered.recruiters],
            model_version_id=model_version.id,
            limit=self.settings.retrieval_top_n,
        )
        if not recruiter_hits:
            return MatchingResult(
                candidate_id=candidate_id,
                eligible_recruiters=len(filtered.recruiters),
                retrieved_recruiters=0,
                recommendations=[],
            )

        recruiters_by_id = {recruiter.id: recruiter for recruiter in filtered.recruiters}
        campaign_ids = sorted(
            {
                link.campaign_id
                for recruiter in recruiters_by_id.values()
                for link in recruiter.campaign_links
                if link.active and link.campaign.status == EntityStatus.ACTIVE and not link.campaign.is_deleted
            },
            key=str,
        )
        campaign_scores = await self._campaign_scores(candidate_vector, campaign_ids, model_version)
        scored = [
            self._score_recruiter(filtered.candidate, recruiters_by_id[uuid.UUID(hit.payload["recruiter_id"])], hit, campaign_scores)
            for hit in recruiter_hits
            if uuid.UUID(hit.payload["recruiter_id"]) in recruiters_by_id
        ]
        scored.sort(
            key=lambda item: (-item.final_score, -item.semantic_score, -item.workload_score, str(item.recruiter.id))
        )
        return MatchingResult(
            candidate_id=candidate_id,
            eligible_recruiters=len(filtered.recruiters),
            retrieved_recruiters=len(scored),
            recommendations=scored[: min(requested_top_k, self.settings.matching_top_k)],
        )

    async def _campaign_scores(
        self,
        candidate_vector: list[float],
        campaign_ids: list[uuid.UUID],
        model_version: ModelVersion,
    ) -> dict[uuid.UUID, float]:
        if not campaign_ids:
            return {}
        campaign_collection = collection_name("campaign", model_version.model_name, model_version.version)
        hits = await self.qdrant.query_campaigns(
            name=campaign_collection,
            vector=candidate_vector,
            campaign_ids=campaign_ids,
            model_version_id=model_version.id,
            limit=len(campaign_ids),
        )
        return {uuid.UUID(hit.payload["campaign_id"]): _normalized_cosine(hit.score) for hit in hits}

    async def _active_model_version(self) -> ModelVersion:
        model_version = await self.model_versions.get_active_for_task(self.model_task)
        if model_version is None:
            raise ActiveModelVersionNotFoundError("Khong tim thay model version active cho matching.")
        if (
            model_version.model_name != self.settings.embedding_model
            or model_version.version != self.settings.embedding_model_version
        ):
            raise ModelVersionConfigurationError("Cau hinh embedding khong khop model version active.")
        return model_version

    def _score_recruiter(
        self,
        candidate,
        recruiter: Recruiter,
        hit: VectorHit,
        campaign_scores: dict[uuid.UUID, float],
    ) -> ScoredRecommendation:
        semantic_score = _normalized_cosine(hit.score)
        active_links = [
            link
            for link in recruiter.campaign_links
            if link.active and link.campaign.status == EntityStatus.ACTIVE and not link.campaign.is_deleted
        ]
        campaign_fit_score = max((campaign_scores.get(link.campaign_id, 0.0) for link in active_links), default=0.0)
        performance_score = _clamp(float(recruiter.conversion_rate)) if recruiter.conversion_rate is not None else self.settings.default_cold_start_performance
        workload_score = _workload_score(recruiter.current_workload, recruiter.max_workload)
        final_score = (
            self.settings.weight_semantic * semantic_score
            + self.settings.weight_campaign * campaign_fit_score
            + self.settings.weight_performance * performance_score
            + self.settings.weight_workload * workload_score
        )
        return ScoredRecommendation(
            recruiter=recruiter,
            active_campaigns=sorted(link.campaign.job_title for link in active_links),
            semantic_score=semantic_score,
            campaign_fit_score=campaign_fit_score,
            performance_score=performance_score,
            workload_score=workload_score,
            final_score=_clamp(final_score),
            reasons=_reasons(candidate, recruiter, semantic_score, campaign_fit_score, workload_score),
        )


def _normalized_cosine(raw_score: float) -> float:
    return _clamp((raw_score + 1.0) / 2.0)


def _workload_score(current: int, maximum: int) -> float:
    if maximum <= 0:
        return 0.0
    return _clamp(1.0 - current / maximum)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _reasons(candidate, recruiter: Recruiter, semantic_score: float, campaign_fit_score: float, workload_score: float) -> list[str]:
    reasons = []
    if candidate.province and any(region.province == candidate.province for region in recruiter.regions):
        reasons.append(f"Phụ trách đúng khu vực {candidate.province}")
    elif candidate.region and any(region.region == candidate.region for region in recruiter.regions):
        reasons.append("Phụ trách cùng vùng tuyển dụng")
    if semantic_score >= 0.7:
        reasons.append("Chuyên môn tuyển dụng phù hợp với nhu cầu công việc")
    if campaign_fit_score >= 0.7:
        reasons.append("Đang phụ trách chiến dịch phù hợp")
    if workload_score >= 0.6:
        reasons.append("Khối lượng công việc hiện còn khả dụng")
    return reasons or ["Đủ điều kiện theo bộ lọc nghiệp vụ"]
