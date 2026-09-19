# Kết quả chạy Spec 005 - 2026-09-19

## Đã xác nhận

- Qdrant integration test: tạo collection tạm, upsert 2 point và filtered query theo recruiter ID/model version pass.
- Toàn bộ test: `16 passed, 1 skipped`.
- API health trả PostgreSQL và Qdrant `ok`.
- Endpoint rebuild trong image chưa cài ML trả `503` với `EMBEDDING_MODEL_UNAVAILABLE` rõ ràng.

## Để rebuild vector PhoBERT thật

1. Đặt `INSTALL_EMBEDDINGS=true` trong `matching_service/.env`.
2. Chạy `docker compose up --build -d` từ `matching_service`.
3. Chờ lần tải PyTorch/Transformers/PhoBERT đầu tiên hoàn tất.
4. Gọi `POST /api/v1/embeddings/recruiters/rebuild`, rồi campaign.

Sau khi cài đủ model, thực hiện bước này trước Spec 006 để semantic retrieval có vector thật.
