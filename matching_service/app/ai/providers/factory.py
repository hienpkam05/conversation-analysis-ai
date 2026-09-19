from functools import lru_cache

from app.ai.providers.base import EmbeddingProvider
from app.ai.providers.phobert_provider import PhoBERTProvider
from app.ai.providers.sentence_transformer_provider import SentenceTransformerProvider
from app.core.config import Settings


def create_embedding_provider(settings: Settings) -> EmbeddingProvider:
    if settings.embedding_provider == "phobert":
        return PhoBERTProvider(
            model_name=settings.embedding_model,
            device=settings.embedding_device,
            max_length=settings.embedding_max_length,
            batch_size=settings.embedding_batch_size,
        )
    return SentenceTransformerProvider(
        model_name=settings.embedding_model,
        device=settings.embedding_device,
        batch_size=settings.embedding_batch_size,
    )


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    return create_embedding_provider(Settings())
