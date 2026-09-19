from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1 import router as v1_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import dispose_database_engine

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging(settings.log_level)
    yield
    await dispose_database_engine()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.include_router(v1_router, prefix=settings.api_v1_prefix)
