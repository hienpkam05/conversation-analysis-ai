from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import EmbeddingProviderUnavailable
from app.db.session import get_db_session
from app.schemas.embedding import RebuildEmbeddingsResponse
from app.services.embedding_rebuild_service import (
    ActiveModelVersionNotFoundError,
    EmbeddingRebuildService,
    ModelVersionConfigurationError,
)
from app.services.qdrant_service import VectorDimensionMismatchError, VectorStoreUnavailableError

router = APIRouter(prefix="/embeddings", tags=["embeddings"])


@router.post("/recruiters/rebuild", response_model=RebuildEmbeddingsResponse)
async def rebuild_recruiters(session: AsyncSession = Depends(get_db_session)) -> RebuildEmbeddingsResponse:
    return await _rebuild(session, "recruiters")


@router.post("/campaigns/rebuild", response_model=RebuildEmbeddingsResponse)
async def rebuild_campaigns(session: AsyncSession = Depends(get_db_session)) -> RebuildEmbeddingsResponse:
    return await _rebuild(session, "campaigns")


async def _rebuild(session: AsyncSession, target: str) -> RebuildEmbeddingsResponse:
    service = EmbeddingRebuildService(session)
    try:
        result = await (service.rebuild_recruiters() if target == "recruiters" else service.rebuild_campaigns())
    except EmbeddingProviderUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "EMBEDDING_MODEL_UNAVAILABLE", "message": str(exc)},
        ) from exc
    except (VectorStoreUnavailableError, VectorDimensionMismatchError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "VECTOR_STORE_UNAVAILABLE", "message": str(exc)},
        ) from exc
    except (ActiveModelVersionNotFoundError, ModelVersionConfigurationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EMBEDDING_CONFIGURATION_INVALID", "message": str(exc)},
        ) from exc
    return RebuildEmbeddingsResponse(**result.__dict__)
