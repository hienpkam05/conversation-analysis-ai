from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.services.health_service import get_health_status

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> JSONResponse:
    response, status_code = await get_health_status()
    return JSONResponse(status_code=status_code, content=response.model_dump(exclude_none=True))
