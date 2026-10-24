from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import EmbeddingProviderUnavailable
from app.db.session import get_db_session
from app.schemas.campaign_search import CampaignSearchRequest, CampaignSearchResponse
from app.services.campaign_search_service import CampaignSearchService, CampaignVectorsNotReady
from app.services.matching_service import ActiveModelVersionNotFoundError, ModelVersionConfigurationError
from app.services.qdrant_service import VectorStoreUnavailableError

router = APIRouter(prefix="/campaigns", tags=["campaign-search"])


@router.post("/search", response_model=CampaignSearchResponse)
async def search_campaigns(request: CampaignSearchRequest, session: AsyncSession = Depends(get_db_session)):
    service = CampaignSearchService(session)
    try:
        return await service.search(request)
    except (CampaignVectorsNotReady, ActiveModelVersionNotFoundError, ModelVersionConfigurationError) as exc:
        raise HTTPException(409, detail={"code": "CAMPAIGN_VECTORS_NOT_READY", "message": str(exc)}) from exc
    except (EmbeddingProviderUnavailable, VectorStoreUnavailableError, SQLAlchemyError) as exc:
        raise HTTPException(503, detail={"code": "CAMPAIGN_SEARCH_UNAVAILABLE", "message": "Model/vector/database chưa sẵn sàng. Kiểm tra log dịch vụ."}) from exc
    finally:
        await service.qdrant.close()
