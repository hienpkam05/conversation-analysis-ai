import uuid
from decimal import Decimal
from types import SimpleNamespace

import numpy as np
import pytest

from app.core.config import Settings
from app.core.enums import EntityStatus, Region
from app.services.hard_filter_service import HardFilterResult
from app.services.matching_service import MatchingService
from app.services.qdrant_service import VectorHit


class FakeProvider:
    model_name = "vinai/phobert-base-v2"
    dimension = 3

    def encode_one(self, text):
        return [1.0, 0.0, 0.0]

    def encode(self, texts):
        return np.array([[1.0, 0.0, 0.0] for _ in texts], dtype=np.float32)


class FakeQdrant:
    def __init__(self, recruiter_hits, campaign_hits):
        self.recruiter_hits = recruiter_hits
        self.campaign_hits = campaign_hits

    async def query_recruiters(self, **kwargs):
        return self.recruiter_hits

    async def query_campaigns(self, **kwargs):
        return self.campaign_hits


@pytest.mark.anyio
async def test_matching_reranks_by_all_component_scores_deterministically():
    model_version = SimpleNamespace(
        id=uuid.uuid4(),
        model_name="vinai/phobert-base-v2",
        version="meanpool-v1",
    )
    candidate = SimpleNamespace(
        id=uuid.uuid4(),
        province="Bắc Ninh",
        region=Region.NORTH,
        desired_job="Công nhân điện tử",
        experience="Lắp ráp linh kiện",
        expected_salary=9_000_000,
    )
    campaign_one = SimpleNamespace(id=uuid.uuid4(), job_title="Công nhân điện tử", status=EntityStatus.ACTIVE, is_deleted=False)
    campaign_three = SimpleNamespace(id=uuid.uuid4(), job_title="Vận hành dây chuyền", status=EntityStatus.ACTIVE, is_deleted=False)
    r1 = SimpleNamespace(
        id=uuid.uuid4(), specialty="Tuyển điện tử", conversion_rate=Decimal("0.72"), current_workload=10, max_workload=50,
        regions=[SimpleNamespace(region=Region.NORTH, province="Bắc Ninh")],
        campaign_links=[SimpleNamespace(active=True, campaign=campaign_one, campaign_id=campaign_one.id)],
    )
    r3 = SimpleNamespace(
        id=uuid.uuid4(), specialty="Tuyển điện tử", conversion_rate=Decimal("0.80"), current_workload=39, max_workload=40,
        regions=[SimpleNamespace(region=Region.NORTH, province="Bắc Ninh")],
        campaign_links=[SimpleNamespace(active=True, campaign=campaign_three, campaign_id=campaign_three.id)],
    )
    hard_filter = SimpleNamespace(eligible_recruiters=lambda candidate_id: _async(HardFilterResult(candidate, [r1, r3])))
    qdrant = FakeQdrant(
        recruiter_hits=[
            VectorHit(uuid.uuid4(), 0.8, {"recruiter_id": str(r1.id)}),
            VectorHit(uuid.uuid4(), 0.9, {"recruiter_id": str(r3.id)}),
        ],
        campaign_hits=[
            VectorHit(uuid.uuid4(), 0.6, {"campaign_id": str(campaign_one.id)}),
            VectorHit(uuid.uuid4(), 0.7, {"campaign_id": str(campaign_three.id)}),
        ],
    )
    service = MatchingService(
        session=None,
        settings=Settings(),
        provider=FakeProvider(),
        qdrant=qdrant,
        hard_filter=hard_filter,
        model_versions=SimpleNamespace(get_active_for_task=lambda task: _async(model_version)),
    )

    result = await service.match(candidate.id, requested_top_k=3)

    assert result.eligible_recruiters == 2
    assert [item.recruiter.id for item in result.recommendations] == [r1.id, r3.id]
    assert result.recommendations[0].final_score > result.recommendations[1].final_score
    assert "Phụ trách đúng khu vực Bắc Ninh" in result.recommendations[0].reasons


async def _async(value):
    return value
