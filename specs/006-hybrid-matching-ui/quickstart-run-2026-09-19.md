# Kết quả chạy Spec 006 - 2026-09-19

- Backend unit test: `17 passed, 1 skipped`.
- Vite production build pass.
- Matching API `GET /api/v1/candidates` trả 3 candidate seed.
- Matching API khi PhoBERT chưa cài trả `503 EMBEDDING_MODEL_UNAVAILABLE` theo thiết kế.
- Frontend Vite chạy tại `http://127.0.0.1:5173`.

Kết quả Top-K thật đang chờ checkpoint PhoBERT được cài và recruiter/campaign embeddings được rebuild theo Spec 005.
