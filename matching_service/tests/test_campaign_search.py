from types import SimpleNamespace
import uuid

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.enums import EntityStatus, Region
from app.schemas.campaign_search import CampaignSearchRequest
from app.services.campaign_search_service import CampaignSearchService, CampaignVectorsNotReady
from app.services.matching_service import ModelVersionConfigurationError
from app.services.profile_builder import build_campaign_profile
from app.services.qdrant_service import VectorHit, collection_name


def test_http_contract_and_service_cleanup_without_database():
    from unittest.mock import AsyncMock
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db.session import get_db_session
    from app.schemas.campaign_search import CampaignSearchResponse
    from app.api.v1 import campaigns as route_module
    from unittest.mock import patch
    async def session():
        yield None
    fake=SimpleNamespace(search=AsyncMock(return_value=CampaignSearchResponse(eligible_campaigns=0,indexed_campaigns=0,recommendations=[])),qdrant=SimpleNamespace(close=AsyncMock()))
    app.dependency_overrides[get_db_session]=session
    try:
        with patch.object(route_module,"CampaignSearchService",return_value=fake),TestClient(app) as client:
            assert client.post("/api/v1/campaigns/search",json={"desired_job":"Lắp ráp","phone":"0987654321"}).status_code==422
            assert client.post("/api/v1/campaigns/search",json={"desired_job":"Lắp ráp"}).status_code==200
            fake.qdrant.close.assert_awaited_once()
            fake.search.side_effect=CampaignVectorsNotReady("vectors unavailable")
            response=client.post("/api/v1/campaigns/search",json={"desired_job":"Lắp ráp"})
            assert response.status_code==409
            assert response.json()["detail"]["code"]=="CAMPAIGN_VECTORS_NOT_READY"
    finally:
        app.dependency_overrides.pop(get_db_session,None)


async def value(item):
    return item


def campaign(**changes):
    values=dict(id=uuid.uuid4(),job_title="Công nhân điện tử",location="Hà Nội",region=Region.NORTH,salary_min=8_000_000,salary_max=12_000_000,
        requirements="Lắp ráp",benefits="Ăn ca",status=EntityStatus.ACTIVE,is_deleted=False)
    return SimpleNamespace(**dict(values,**changes))


def fixture(rows, hits=None, refs_missing=False):
    settings=Settings()
    version=SimpleNamespace(id=uuid.uuid4(),model_name=settings.embedding_model,version=settings.embedding_model_version)
    name=collection_name("campaign",version.model_name,version.version)
    refs={row.id:SimpleNamespace(point_id=uuid.uuid4(),qdrant_collection=name,profile_hash=build_campaign_profile(row,version.id).profile_hash) for row in rows}
    default_hits=[VectorHit(refs[row.id].point_id,.8,{"campaign_id":str(row.id),"model_version_id":str(version.id),"profile_hash":refs[row.id].profile_hash}) for row in rows]
    calls=[]

    class Provider:
        def encode_one(self,text):
            calls.append(("profile",text))
            return [1,0,0]
    class Qdrant:
        async def query_campaigns(self,**kwargs):
            calls.append(("ids",kwargs["campaign_ids"]))
            return default_hits if hits is None else hits
    service=CampaignSearchService(None,settings=settings,provider=Provider(),qdrant=Qdrant(),
        campaigns=SimpleNamespace(find_active_for_embedding=lambda:value(rows)),
        refs=SimpleNamespace(find_for_objects=lambda **kwargs:value({} if refs_missing else refs)),
        versions=SimpleNamespace(get_active_for_task=lambda task:value(version)))
    return service,version,refs,default_hits,calls


def test_schema_rejects_personal_data_and_invalid_filters():
    for changes in ({"phone":"0987654321"},{"full_name":"An"},{"top_k":True},{"expected_salary":True},{"strict_salary":True},{"region":"other"},{"desired_job":" "}):
        with pytest.raises(ValidationError):
            CampaignSearchRequest(**dict({"desired_job":"Lắp ráp"},**changes))


@pytest.mark.anyio
async def test_active_region_salary_filters_are_applied_before_vector_search():
    included=campaign()
    rows=[included,campaign(region=Region.SOUTH),campaign(region=None),campaign(salary_max=None),campaign(salary_max=7_000_000),campaign(is_deleted=True),campaign(status=EntityStatus.INACTIVE)]
    service,_,_,_,calls=fixture(rows)
    result=await service.search(CampaignSearchRequest(desired_job="Lắp ráp",region="north",expected_salary=10_000_000,strict_salary=True))
    self_ids=[row.campaign_id for row in result.recommendations]
    assert self_ids==[included.id]
    assert result.eligible_campaigns==1
    assert calls[-1]==("ids",[included.id])
    assert "Ca làm" in result.recommendations[0].warnings[0]


@pytest.mark.anyio
async def test_empty_business_candidates_do_not_load_model_or_vectors():
    service,_,_,_,calls=fixture([campaign(region=Region.SOUTH)])
    result=await service.search(CampaignSearchRequest(desired_job="Lắp ráp",region="north"))
    assert result.recommendations==[] and result.model_version_id is None
    assert calls==[]


@pytest.mark.anyio
async def test_no_indexed_vectors_is_not_fake_success_empty_result():
    service,_,_,_,calls=fixture([campaign()],refs_missing=True)
    with pytest.raises(CampaignVectorsNotReady):
        await service.search(CampaignSearchRequest(desired_job="Lắp ráp"))
    assert calls==[]


@pytest.mark.anyio
async def test_stale_profile_and_wrong_model_are_rejected():
    row=campaign()
    service,version,refs,_,_=fixture([row])
    refs[row.id].profile_hash="stale"
    with pytest.raises(CampaignVectorsNotReady):
        await service.search(CampaignSearchRequest(desired_job="Lắp ráp"))
    version.version="other-version"
    with pytest.raises(ModelVersionConfigurationError):
        await service.search(CampaignSearchRequest(desired_job="Lắp ráp"))


@pytest.mark.anyio
async def test_payload_injection_nonfinite_scores_and_duplicate_hits_are_not_returned():
    row=campaign()
    hits=[]
    service,version,refs,good,_=fixture([row],hits=hits)
    ref=refs[row.id]
    hits.extend([VectorHit(ref.point_id,.7,good[0].payload),VectorHit(ref.point_id,.9,good[0].payload),
        VectorHit(ref.point_id,float("nan"),good[0].payload),VectorHit(uuid.uuid4(),1,good[0].payload),
        VectorHit(ref.point_id,1,dict(good[0].payload,campaign_id=str(uuid.uuid4()))),
        VectorHit(ref.point_id,1,dict(good[0].payload,model_version_id=str(uuid.uuid4())))])
    result=await service.search(CampaignSearchRequest(desired_job="Lắp ráp"))
    assert len(result.recommendations)==1
    assert result.recommendations[0].semantic_score==.9


@pytest.mark.anyio
async def test_soft_salary_does_not_exclude_unknown_salary():
    row=campaign(salary_max=None)
    service,_,_,_,_=fixture([row])
    result=await service.search(CampaignSearchRequest(desired_job="Lắp ráp",expected_salary=10_000_000))
    assert len(result.recommendations)==1
    assert any("lương tối đa" in warning for warning in result.recommendations[0].warnings)
