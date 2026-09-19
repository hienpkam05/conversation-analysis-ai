# Đặc tả 005: Qdrant Collection và Rebuild Embeddings

## Mục tiêu

Tạo vector store cho recruiter/campaign profiles, liên kết Qdrant với PostgreSQL bằng `embedding_refs`, và cung cấp nền truy hồi semantic có filter recruiter đủ điều kiện.

## Phạm vi

- Tạo collection theo `object_type + model_name + model_version`.
- Lấy vector dimension từ provider, không hardcode trong Qdrant service.
- Tạo payload index và chỉ ghi metadata không PII.
- Upsert vector batch, point UUID ổn định và `embedding_refs` idempotent.
- Rebuild recruiter/campaign qua script và API.
- Query recruiter với filter `eligible_recruiter_ids` và `model_version_id`.

## Ngoài phạm vi

- Chưa tạo endpoint matching Top-K hay re-ranking: thuộc Spec 006.
- Candidate embedding vẫn query realtime ở phase sau, không lưu mặc định.
- Chưa tự động tải dependency/model PhoBERT trong Docker image nền.

## Endpoint

```text
POST /api/v1/embeddings/recruiters/rebuild
POST /api/v1/embeddings/campaigns/rebuild
```

Provider không sẵn sàng trả `503` với code `EMBEDDING_MODEL_UNAVAILABLE`; Qdrant lỗi trả `503` với code `VECTOR_STORE_UNAVAILABLE`.
