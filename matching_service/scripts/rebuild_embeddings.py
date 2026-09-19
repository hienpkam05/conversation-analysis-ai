import argparse
import asyncio

from app.db.session import AsyncSessionLocal, dispose_database_engine
from app.services.embedding_rebuild_service import EmbeddingRebuildService


async def rebuild(target: str) -> None:
    async with AsyncSessionLocal() as session:
        service = EmbeddingRebuildService(session)
        result = await (service.rebuild_recruiters() if target == "recruiters" else service.rebuild_campaigns())
        print(
            f"Rebuild {result.object_type}: total={result.total}, "
            f"embedded={result.embedded}, skipped={result.skipped}, collection={result.collection_name}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild Qdrant embeddings")
    parser.add_argument("target", choices=["recruiters", "campaigns"])
    arguments = parser.parse_args()
    try:
        asyncio.run(rebuild(arguments.target))
    finally:
        asyncio.run(dispose_database_engine())


if __name__ == "__main__":
    main()
