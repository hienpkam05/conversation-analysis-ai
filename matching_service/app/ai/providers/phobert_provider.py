from __future__ import annotations

from typing import Any

import numpy as np

from app.ai.providers.base import EmbeddingProviderUnavailable


class PhoBERTProvider:
    """PhoBERT backbone voi masked mean pooling va L2 normalization."""

    def __init__(self, *, model_name: str, device: str, max_length: int, batch_size: int):
        self._model_name = model_name
        self._device = device
        self._max_length = max_length
        self._batch_size = batch_size
        self._tokenizer: Any | None = None
        self._model: Any | None = None
        self._torch: Any | None = None
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
            dimension = self._dimension or 0
            return np.empty((0, dimension), dtype=np.float32)

        self._ensure_model()
        assert self._tokenizer is not None and self._model is not None and self._torch is not None

        vectors: list[np.ndarray] = []
        for start in range(0, len(texts), self._batch_size):
            batch = texts[start : start + self._batch_size]
            encoded = self._tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=self._max_length,
                return_tensors="pt",
            )
            encoded = {key: value.to(self._device) for key, value in encoded.items()}
            with self._torch.inference_mode():
                hidden_state = self._model(**encoded).last_hidden_state
                attention_mask = encoded["attention_mask"].unsqueeze(-1).expand(hidden_state.size()).float()
                pooled = (hidden_state * attention_mask).sum(dim=1) / attention_mask.sum(dim=1).clamp(min=1e-9)
                pooled = self._torch.nn.functional.normalize(pooled, p=2, dim=1)
            vectors.append(pooled.cpu().numpy().astype(np.float32))
        return np.vstack(vectors)

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        try:
            import torch
            from transformers import AutoModel, AutoTokenizer
        except ImportError as exc:
            raise EmbeddingProviderUnavailable(
                "Chua cai dependency embedding. Chay pip install '.[embeddings]' trong matching_service."
            ) from exc

        try:
            self._tokenizer = AutoTokenizer.from_pretrained(self._model_name)
            self._model = AutoModel.from_pretrained(self._model_name).to(self._device)
            self._model.eval()
            self._torch = torch
            self._dimension = int(self._model.config.hidden_size)
        except Exception as exc:
            raise EmbeddingProviderUnavailable(f"Khong the tai PhoBERT '{self._model_name}': {exc}") from exc
