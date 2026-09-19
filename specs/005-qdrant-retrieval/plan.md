# Kế hoạch 005

1. Tạo Qdrant service cho collection/index/upsert/query.
2. Tạo repository `embedding_refs` và model version active lookup.
3. Tạo rebuild service đọc profile bằng eager loading, encode batch, ghi Qdrant rồi upsert ref.
4. Thêm endpoint/script rebuild.
5. Test Qdrant thật bằng collection tạm; test rebuild idempotent bằng provider giả.

## Payload Qdrant

- Recruiter: `recruiter_id`, `model_version_id`, `region_tags`, `profile_hash`.
- Campaign: `campaign_id`, `model_version_id`, `status`, `location_tags`, `profile_hash`.
- Tuyệt đối không có `full_name`, `phone` hay profile text.
