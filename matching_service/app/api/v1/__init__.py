from fastapi import APIRouter

from app.api.v1.eligibility import router as eligibility_router
from app.api.v1.embeddings import router as embeddings_router
from app.api.v1.health import router as health_router
from app.api.v1.candidates import router as candidates_router
from app.api.v1.matching import router as matching_router
from app.api.v1.campaigns import router as campaigns_router

router = APIRouter()
router.include_router(health_router)
router.include_router(eligibility_router)
router.include_router(embeddings_router)
router.include_router(candidates_router)
router.include_router(matching_router)
router.include_router(campaigns_router)
