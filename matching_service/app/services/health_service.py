import asyncio
from dataclasses import dataclass

from qdrant_client import AsyncQdrantClient
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import engine
from app.schemas.health import HealthResponse


@dataclass
class DependencyCheck:
    name: str
    status: str
    detail: str | None = None


async def check_postgres() -> DependencyCheck:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return DependencyCheck(name="postgres", status="ok")
    except Exception as exc:
        return DependencyCheck(name="postgres", status="error", detail=str(exc))


async def check_qdrant() -> DependencyCheck:
    settings = get_settings()
    client = AsyncQdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
    try:
        await client.get_collections()
        return DependencyCheck(name="qdrant", status="ok")
    except Exception as exc:
        return DependencyCheck(name="qdrant", status="error", detail=str(exc))
    finally:
        await client.close()


async def get_health_status() -> tuple[HealthResponse, int]:
    postgres, qdrant = await asyncio.gather(check_postgres(), check_qdrant())
    failed = [item for item in (postgres, qdrant) if item.status != "ok"]
    if not failed:
        return HealthResponse(status="ok", postgres="ok", qdrant="ok"), 200

    details = "; ".join(f"{item.name}: {item.detail}" for item in failed)
    return (
        HealthResponse(
            status="error",
            postgres=postgres.status,
            qdrant=qdrant.status,
            detail=details,
        ),
        503,
    )
