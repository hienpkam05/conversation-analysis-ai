from __future__ import annotations

from typing import Any

import numpy as np

from app.ai.providers.base import EmbeddingProviderUnavailable


class SentenceTransformerProvider:
    """Provider sentence embedding co san normalization cho cosine similarity."""

    def __init__(self, *, model_name: str, device: str, batch_size: int):
        self._model_name = model_name
        self._device = device
        self._batch_size = batch_size
        self._model: Any | None = None
        self._dimension: int | None = None

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        self._ensure_model()
        assert self._dimension is not None
        return self._dimension

    def encode_one(self, text: str) -> list[float]:
        return self.encode([text])[0].tolist()

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self._dimension or 0), dtype=np.float32)
        self._ensure_model()
        assert self._model is not None
        vectors = self._model.encode(
            texts,
            batch_size=self._batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return np.asarray(vectors, dtype=np.float32)

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise EmbeddingProviderUnavailable(
                "Chua cai dependency embedding. Chay pip install '.[embeddings]' trong matching_service."
            ) from exc

        try:
            self._model = SentenceTransformer(self._model_name, device=self._device)
            self._dimension = int(self._model.get_sentence_embedding_dimension())
        except Exception as exc:
            raise EmbeddingProviderUnavailable(
                f"Khong the tai Sentence Transformer '{self._model_name}': {exc}"
            ) from exc
