# Matching Service

FastAPI service độc lập cho bài toán ghép ứng viên với nhân viên tuyển dụng. Đặc tả 001 tạo nền kỹ thuật; Đặc tả 002 bổ sung schema PostgreSQL, Alembic migration và dữ liệu seed. Thuật toán matching, embedding và Qdrant collection chưa được triển khai.

## Thành phần

- FastAPI tại `http://localhost:8001`
- PostgreSQL cho dữ liệu nghiệp vụ
- Qdrant cho vector retrieval ở các đặc tả tiếp theo
- SQLAlchemy 2.x async và Alembic

## Chạy bằng Docker Compose

Bạn đang có PostgreSQL ở `5432` và Qdrant ở `6333`, nên Compose mặc định dùng `5433`, `6335`, `6336` cho bộ hạ tầng riêng của service để không bị xung đột.

```powershell
cd matching_service
Copy-Item .env.example .env
docker compose up --build
```

Kiểm tra API ở cửa sổ PowerShell khác:

```powershell
Invoke-RestMethod http://localhost:8001/api/v1/health
```

Kết quả mong đợi:

```json
{
  "status": "ok",
  "service": "candidate-recruiter-matching",
  "postgres": "ok",
  "qdrant": "ok"
}
```

Dừng service:

```powershell
docker compose down
```

Thêm `-v` vào lệnh trên chỉ khi bạn chủ động muốn xóa dữ liệu của Compose.

## Chạy trực tiếp trên máy local

Phần này dùng PostgreSQL `5432` và Qdrant `6333` mà bạn đã chạy thủ công.

```powershell
cd matching_service
Copy-Item .env.example .env
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8001
```

Nếu PowerShell chặn activate script, dùng trực tiếp `.venv\Scripts\python.exe` để chạy các lệnh bên dưới.

## Migration

Tạo toàn bộ bảng nghiệp vụ của Đặc tả 002:

```powershell
alembic current
alembic upgrade head
```

Migration tạo: `candidates`, `recruiters`, `recruiter_regions`, `campaigns`, `recruiter_campaigns`, `model_versions`, `embedding_refs`, `matching_runs`, `matching_results`.

## Seed dữ liệu demo

Sau khi migration hoàn tất, chạy:

```powershell
python -m scripts.seed_demo
```

Khi chạy trong Docker Compose:

```powershell
docker compose exec api python -m scripts.seed_demo
```

Script có thể chạy lặp lại mà không tạo trùng dữ liệu. Nó tạo 5 recruiter, 5 campaign, 3 candidate và một model version mẫu. Dữ liệu `full_name`/`phone` chỉ tồn tại trong PostgreSQL; các đặc tả sau không được đưa chúng vào profile hay vector Qdrant.

## Test

```powershell
pytest
```

## Biến môi trường quan trọng

| Biến | Ý nghĩa |
| --- | --- |
| `DATABASE_URL` | Chuỗi kết nối PostgreSQL async |
| `QDRANT_URL` | Địa chỉ Qdrant |
| `MATCHING_TOP_K` | Số kết quả mục tiêu, mặc định 3 |
| `RETRIEVAL_TOP_N` | Số recruiter được lấy trước rerank; phải >= `MATCHING_TOP_K` |
| `STRICT_REGION` | Bật lọc cứng theo vùng ở đặc tả sau |
| `REQUIRE_ACTIVE_CAMPAIGN` | Yêu cầu recruiter có campaign active ở đặc tả sau |
| `WEIGHT_*` | Bốn trọng số semantic/campaign/performance/workload phải có tổng bằng 1.0 |

Không đưa `.env` lên Git. Đặc tả tiếp theo sẽ bổ sung repository và hard filter; embedding/Qdrant collection sẽ làm sau đó.

## Hard filter recruiter

Đặc tả 003 có endpoint kiểm tra recruiter đủ điều kiện cho một candidate:

```text
GET /api/v1/candidates/{candidate_id}/eligible-recruiters
```

Hard filter chỉ trả recruiter khi đồng thời active, chưa soft-delete, còn capacity; đồng thời lọc region và campaign active theo `STRICT_REGION` và `REQUIRE_ACTIVE_CAMPAIGN`. Query dùng eager loading cho region/campaign, không truy vấn database từng recruiter.

## Profile và embedding

Đặc tả 004 bổ sung profile deterministic cho candidate, recruiter và campaign. Profile không chứa `full_name` hay `phone`; nó chỉ dùng thuộc tính nghiệp vụ cần cho matching. Provider hỗ trợ PhoBERT mean-pooling và Sentence Transformers qua cùng một interface.

Cài dependency ML khi chuẩn bị encode/rebuild vector:

```powershell
pip install -e ".[embeddings,dev]"
```

Cấu hình mặc định trong `.env.example` dùng PhoBERT trên CPU. Model chỉ tải ở lần `encode()` đầu tiên, vì vậy API health và hard filter vẫn khởi động nhanh. Qdrant collection, rebuild và semantic retrieval sẽ được thêm ở Đặc tả 005.

## Qdrant rebuild embeddings

Đặc tả 005 tạo collection Qdrant versioned, payload index và liên kết PostgreSQL `embedding_refs`. Payload chỉ chứa ID nghiệp vụ, model version, tag vùng/địa điểm và hash; không chứa PII hoặc profile text.

Khi đã cài dependency ML (`pip install -e ".[embeddings,dev]"`), chạy rebuild từ môi trường local:

```powershell
python -m scripts.rebuild_embeddings recruiters
python -m scripts.rebuild_embeddings campaigns
```

Hoặc gọi endpoint:

```text
POST /api/v1/embeddings/recruiters/rebuild
POST /api/v1/embeddings/campaigns/rebuild
```

Chạy lại khi profile không đổi sẽ trả `embedded: 0`; thay model/version sẽ tạo collection mới thay vì trộn vector khác dimension. Docker API mặc định không cài extra ML để image khởi động nhẹ, nên endpoint sẽ trả `503 EMBEDDING_MODEL_UNAVAILABLE` cho tới khi cài dependency embedding.

Để API Docker cài PhoBERT thật, đặt `INSTALL_EMBEDDINGS=true` trong `.env` rồi chạy `docker compose up --build -d`. Docker dùng PyTorch CPU-only để không tải CUDA/NVIDIA packages; lần build đầu vẫn cần tải PyTorch, Transformers và checkpoint PhoBERT nên sẽ mất khá lâu.

Extra `embeddings` chỉ cài PhoBERT mặc định. Khi cần thử baseline khác, cài thêm `pip install -e ".[sentence-transformers]"` trong môi trường phù hợp.
