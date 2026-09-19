# Hợp đồng EmbeddingProvider

```python
class EmbeddingProvider(Protocol):
    @property
    def model_name(self) -> str: ...

    @property
    def dimension(self) -> int: ...

    def encode(self, texts: list[str]) -> np.ndarray: ...

    def encode_one(self, text: str) -> list[float]: ...
```

## Điều kiện đầu ra

- `encode` trả `float32` có shape `(len(texts), dimension)`.
- Vector được L2 normalize.
- `encode_one(text)` tương đương `encode([text])[0]`.
- Lỗi thiếu dependency, model không tải được hoặc inference lỗi được biểu diễn bằng `EmbeddingProviderUnavailable`.
