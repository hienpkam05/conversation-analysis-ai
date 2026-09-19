import os
import uuid

import pytest
from qdrant_client import AsyncQdrantClient, models

from app.core.config import Settings
from app.services.qdrant_service import QdrantService, collection_name


def test_collection_name_is_stable_and_safe():
    assert (
        collection_name("recruiter", "vinai/phobert-base-v2", "meanpool-v1")
        == "recruiter_embeddings__vinai_phobert_base_v2_meanpool_v1"
    )


@pytest.mark.anyio
async def test_qdrant_upsert_and_filtered_query():
    qdrant_url = os.getenv("TEST_QDRANT_URL")
    if not qdrant_url:
        pytest.skip("Dat TEST_QDRANT_URL de chay integration test Qdrant.")

    client = AsyncQdrantClient(url=qdrant_url)
    service = QdrantService(settings=Settings(qdrant_url=qdrant_url), client=client)
    name = f"spec005_test_{uuid.uuid4().hex}"
    model_version_id = uuid.uuid4()
    allowed_recruiter_id = uuid.uuid4()
    blocked_recruiter_id = uuid.uuid4()
    try:
        created = await service.ensure_collection(name, 3, ["recruiter_id", "model_version_id"])
        assert created is True
        await service.upsert(
            name,
            [
                models.PointStruct(
                    id=uuid.uuid4(),
                    vector=[1.0, 0.0, 0.0],
                    payload={
                        "recruiter_id": str(allowed_recruiter_id),
                        "model_version_id": str(model_version_id),
                    },
                ),
                models.PointStruct(
                    id=uuid.uuid4(),
                    vector=[1.0, 0.0, 0.0],
                    payload={
                        "recruiter_id": str(blocked_recruiter_id),
                        "model_version_id": str(model_version_id),
                    },
                ),
            ],
        )

        hits = await service.query_recruiters(
            name=name,
            vector=[1.0, 0.0, 0.0],
            eligible_recruiter_ids=[allowed_recruiter_id],
            model_version_id=model_version_id,
            limit=10,
        )

        assert len(hits) == 1
        assert hits[0].payload["recruiter_id"] == str(allowed_recruiter_id)
        assert hits[0].score == pytest.approx(1.0)
    finally:
        await client.delete_collection(name)
        await service.close()
