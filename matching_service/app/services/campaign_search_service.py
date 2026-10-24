import math
from types import SimpleNamespace
import uuid

from app.ai.providers import get_embedding_provider
from app.core.config import get_settings
from app.core.enums import EntityStatus
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.embedding_ref_repository import EmbeddingRefRepository
from app.repositories.model_version_repository import ModelVersionRepository
from app.schemas.campaign_search import CampaignRecommendation, CampaignSearchResponse
from app.services.matching_service import ActiveModelVersionNotFoundError, ModelVersionConfigurationError
from app.services.profile_builder import build_candidate_profile, build_campaign_profile
from app.services.qdrant_service import QdrantService, collection_name


class CampaignVectorsNotReady(RuntimeError):
    pass


class CampaignSearchService:
    def __init__(self, session, *, settings=None, provider=None, qdrant=None, campaigns=None, refs=None, versions=None):
        self.settings = settings or get_settings()
        self.provider = provider or get_embedding_provider()
        self.qdrant = qdrant or QdrantService(settings=self.settings)
        self.campaigns = campaigns or CampaignRepository(session)
        self.refs = refs or EmbeddingRefRepository(session)
        self.versions = versions or ModelVersionRepository(session)

    async def search(self, request):
        rows = await self.campaigns.find_active_for_embedding()
        rows = [row for row in rows if row.status == EntityStatus.ACTIVE and not row.is_deleted
            and (request.region is None or row.region == request.region)
            and (not request.strict_salary or row.salary_max is not None and row.salary_max >= request.expected_salary)]
        if not rows:
            return CampaignSearchResponse(eligible_campaigns=0, indexed_campaigns=0, recommendations=[], message="Không có chiến dịch đang hoạt động thỏa bộ lọc đã chọn.")
        version = await self.versions.get_active_for_task("recruiter_matching_embedding")
        if version is None:
            raise ActiveModelVersionNotFoundError("Chưa có embedding version active.")
        if version.model_name != self.settings.embedding_model or version.version != self.settings.embedding_model_version:
            raise ModelVersionConfigurationError("Cấu hình embedding không khớp model version active.")
        collection = collection_name("campaign", version.model_name, version.version)
        refs = await self.refs.find_for_objects(object_type="campaign", object_ids=[row.id for row in rows], model_version_id=version.id, embedding_type="semantic_profile")
        valid = {row.id: row for row in rows if row.id in refs
            and refs[row.id].qdrant_collection == collection
            and refs[row.id].profile_hash == build_campaign_profile(row, version.id).profile_hash}
        if not valid:
            raise CampaignVectorsNotReady("Chưa có vector chiến dịch hiện hành; rebuild campaigns trước.")
        profile = build_candidate_profile(SimpleNamespace(province=request.desired_location, region=request.region,
            desired_job=request.desired_job, experience=request.experience, expected_salary=request.expected_salary), version.id)
        # The same candidate-profile schema as recruiter matching; shift is not a structured campaign filter.
        vector = self.provider.encode_one(profile.text)
        hits = await self.qdrant.query_campaigns(name=collection, vector=vector, campaign_ids=list(valid), model_version_id=version.id, limit=min(len(valid), max(request.top_k * 3, 10)))
        scored = {}
        for hit in hits:
            try:
                key = uuid.UUID(hit.payload["campaign_id"])
                if key not in valid or hit.payload.get("model_version_id") != str(version.id) or hit.payload.get("profile_hash") != refs[key].profile_hash or hit.point_id != refs[key].point_id or not math.isfinite(hit.score) or not -1.00001 <= hit.score <= 1.00001:
                    continue
                scored[key] = max(scored.get(key, -1), max(-1.0, min(1.0, hit.score)))
            except (ValueError, TypeError, KeyError, AttributeError):
                continue
        if not scored:
            raise CampaignVectorsNotReady("Qdrant chưa trả vector chiến dịch hợp lệ theo dữ liệu hiện tại.")
        recommendations = []
        for key in sorted(scored, key=lambda key: (-scored[key], str(key)))[:request.top_k]:
            row = valid[key]
            warnings = ["Ca làm và ngày bắt đầu chưa có dữ liệu có cấu trúc; cần đối chiếu với tư vấn viên."]
            if row.salary_max is None:
                warnings.append("Chiến dịch chưa có lương tối đa để đối chiếu.")
            if request.desired_location:
                warnings.append("Địa điểm cụ thể chỉ dùng trong tìm ngữ nghĩa; chưa kiểm chứng khoảng cách hoặc địa chỉ.")
            recommendations.append(CampaignRecommendation(campaign_id=key, job_title=row.job_title, location=row.location,
                region=row.region, salary_min=row.salary_min, salary_max=row.salary_max, requirements=row.requirements,
                benefits=row.benefits, semantic_score=scored[key], warnings=warnings))
        return CampaignSearchResponse(model_version_id=version.id, model_name=version.model_name,
            eligible_campaigns=len(rows), indexed_campaigns=len(valid), recommendations=recommendations,
            message=f"{len(rows) - len(valid)} chiến dịch chưa có vector hiện hành." if len(rows) > len(valid) else None)
