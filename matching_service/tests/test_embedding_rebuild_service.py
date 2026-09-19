import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import numpy as np
import pytest

from app.core.config import Settings
from app.core.enums import EntityStatus, Region
from app.services.embedding_rebuild_service import EmbeddingRebuildService


class FakeProvider:
    model_name = "vinai/phobert-base-v2"
    dimension = 3

    def __init__(self):
        self.calls: list[list[str]] = []

    def encode(self, texts: list[str]) -> np.ndarray:
        self.calls.append(texts)
        return np.array([[1.0, 0.0, 0.0] for _ in texts], dtype=np.float32)

    def encode_one(self, text: str) -> list[float]:
        return self.encode([text])[0].tolist()


class FakeQdrant:
    def __init__(self):
        self.collection_created = True
        self.upserted_points = []

    async def ensure_collection(self, name, dimension, payload_fields):
        assert dimension == 3
        return self.collection_created

    async def upsert(self, name, points):
        self.upserted_points.extend(points)


class FakeRefs:
    def __init__(self):
        self.values = {}

    async def find_for_objects(self, **kwargs):
        return self.values

    async def upsert(self, **kwargs):
        self.values[kwargs["object_id"]] = SimpleNamespace(
            profile_hash=kwargs["profile_hash"],
            qdrant_collection=kwargs["qdrant_collection"],
        )


@pytest.mark.anyio
async def test_rebuild_recruiters_is_idempotent_and_payload_has_no_pii():
    model_version = SimpleNamespace(
        id=uuid.uuid4(),
        model_name="vinai/phobert-base-v2",
        version="meanpool-v1",
    )
    campaign = SimpleNamespace(job_title="Công nhân điện tử", status=EntityStatus.ACTIVE, is_deleted=False)
    recruiter = SimpleNamespace(
        id=uuid.uuid4(),
        full_name="Tên không được phép đưa vào payload",
        specialty="Tuyển công nhân điện tử",
        regions=[SimpleNamespace(region=Region.NORTH, province="Bắc Ninh")],
        campaign_links=[SimpleNamespace(active=True, campaign=campaign)],
    )
    provider = FakeProvider()
    qdrant = FakeQdrant()
    session = SimpleNamespace(commit=AsyncMock())
    service = EmbeddingRebuildService(
        session,
        settings=Settings(),
        provider=provider,
        qdrant=qdrant,
    )
    service.models = SimpleNamespace(get_active_for_task=AsyncMock(return_value=model_version))
    service.recruiters = SimpleNamespace(find_active_for_embedding=AsyncMock(return_value=[recruiter]))
    service.refs = FakeRefs()

    first = await service.rebuild_recruiters()
    qdrant.collection_created = False
    second = await service.rebuild_recruiters()

    assert first.total == 1
    assert first.embedded == 1
    assert second.embedded == 0
    assert second.skipped == 1
    assert len(provider.calls) == 1
    assert qdrant.upserted_points[0].payload["recruiter_id"] == str(recruiter.id)
    assert "Tên không được phép đưa vào payload" not in qdrant.upserted_points[0].payload.values()
