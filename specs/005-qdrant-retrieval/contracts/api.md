# API Embedding Rebuild

## `POST /api/v1/embeddings/recruiters/rebuild`

Response `200`:

```json
{
  "object_type": "recruiter",
  "collection_name": "recruiter_embeddings__vinai_phobert_base_v2_meanpool_v1",
  "model_version_id": "uuid",
  "total": 5,
  "embedded": 5,
  "skipped": 0
}
```

Endpoint campaign có cùng response, `object_type` là `campaign`.

| HTTP | Code | Ý nghĩa |
| --- | --- | --- |
| 503 | `EMBEDDING_MODEL_UNAVAILABLE` | Thiếu dependency hoặc model không tải được. |
| 503 | `VECTOR_STORE_UNAVAILABLE` | Qdrant không sẵn sàng hoặc dimension sai. |
| 409 | `EMBEDDING_CONFIGURATION_INVALID` | Model config và model version active không khớp. |
