# Dữ liệu 005

Không tạo migration mới. `embedding_refs` đã tồn tại từ Spec 002 và được ghi qua PostgreSQL upsert với unique key:

```text
(object_type, object_id, model_version_id, embedding_type)
```

| Trường | Ý nghĩa |
| --- | --- |
| `qdrant_collection` | Collection versioned đang chứa point. |
| `point_id` | UUID ổn định tạo từ object type/model version/object ID. |
| `profile_hash` | Dấu vết profile đã encode, quyết định có cần rebuild. |
