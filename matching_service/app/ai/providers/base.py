from typing import Protocol

import numpy as np


class EmbeddingProviderUnavailable(RuntimeError):
    """Khong the nap dependency hoac mo hinh embedding da cau hinh."""


class EmbeddingProvider(Protocol):
    @property
    def model_name(self) -> str: ...

    @property
    def dimension(self) -> int: ...

    def encode(self, texts: list[str]) -> np.ndarray: ...

    def encode_one(self, text: str) -> list[float]: ...
