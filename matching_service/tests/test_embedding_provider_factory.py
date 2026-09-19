from app.ai.providers import PhoBERTProvider, SentenceTransformerProvider, create_embedding_provider
from app.core.config import Settings


def test_factory_creates_phobert_without_loading_the_model():
    provider = create_embedding_provider(Settings(embedding_provider="phobert"))

    assert isinstance(provider, PhoBERTProvider)
    assert provider.model_name == "vinai/phobert-base-v2"


def test_factory_creates_sentence_transformer_without_loading_the_model():
    provider = create_embedding_provider(
        Settings(
            embedding_provider="sentence_transformer",
            embedding_model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        )
    )

    assert isinstance(provider, SentenceTransformerProvider)
