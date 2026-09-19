# API Matching

## `GET /api/v1/candidates`

Trả candidate không soft-delete với region, tỉnh, công việc mong muốn, kinh nghiệm và lương kỳ vọng. Không trả số điện thoại hoặc họ tên sang UI matching.

## `POST /api/v1/matching/candidates/{candidate_id}`

Request:

```json
{ "top_k": 3 }
```

Response chứa `eligible_recruiters`, `retrieved_recruiters` và recommendations. Mỗi recommendation có rank, 4 component scores, final score, workload, campaign active và reasons.

| HTTP | Code | Ý nghĩa |
| --- | --- | --- |
| 404 | `CANDIDATE_NOT_FOUND` | Candidate không tồn tại. |
| 422 | `CANDIDATE_REGION_REQUIRED` | Strict region bật nhưng candidate thiếu vùng. |
| 503 | `EMBEDDING_MODEL_UNAVAILABLE` | PhoBERT chưa cài/tải được. |
| 503 | `VECTOR_STORE_UNAVAILABLE` | Qdrant/collection/vector không sẵn sàng. |
| 409 | `EMBEDDING_CONFIGURATION_INVALID` | Config model và model version active không khớp. |
