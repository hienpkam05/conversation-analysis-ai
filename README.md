# AI Recruitment Lab

Ứng dụng hỗ trợ tuyển dụng lao động tạm thời gồm hai chức năng:

- Chuyển file ghi âm tư vấn tuyển dụng thành văn bản.
- Ghép ứng viên với recruiter phù hợp dựa trên điều kiện nghiệp vụ, PhoBERT và Qdrant.

## Kiến trúc

| Thành phần | Công nghệ | Địa chỉ khi chạy local |
| --- | --- | --- |
| Giao diện | Vue 3 + Vite | `http://127.0.0.1:5173` |
| API chuyển audio | Django | `http://127.0.0.1:8000` |
| API matching | FastAPI | `http://127.0.0.1:8001` |
| Dữ liệu nghiệp vụ | PostgreSQL trong Docker | `localhost:5433` |
| Vector database | Qdrant trong Docker | `http://localhost:6335/dashboard` |

Mỗi máy chạy Docker sẽ có PostgreSQL và Qdrant riêng. Dữ liệu không được dùng chung với máy khác.

## Yêu cầu

Để dùng chức năng ghép ứng viên:

- Git.
- Docker Desktop đang chạy.
- Internet ở lần đầu để tải image, PyTorch CPU, Transformers và checkpoint PhoBERT.

Để mở giao diện Vue, cài thêm Node.js 20 LTS hoặc mới hơn.

Để chạy chức năng chuyển audio ở máy local, cài thêm Python 3.12 và FFmpeg. Hướng dẫn chi tiết nằm ở [README_WEB.md](README_WEB.md).

## Chạy nhanh chức năng Matching

### 1. Clone dự án

```powershell
git clone <URL_REPOSITORY_CUA_BAN>
cd NCKH
```

### 2. Cấu hình và khởi động Docker

```powershell
cd matching_service
Copy-Item .env.example .env
```

Mở file `.env`, đổi dòng sau thành:

```env
INSTALL_EMBEDDINGS=true
```

Sau đó build và chạy dịch vụ:

```powershell
docker compose up --build -d
```

Lần đầu có thể mất khá lâu vì Docker cần tải PyTorch CPU và PhoBERT. Các lần sau Docker dùng cache nên nhanh hơn.

Kiểm tra ba service đã chạy:

```powershell
docker compose ps
Invoke-RestMethod http://127.0.0.1:8001/api/v1/health
```

Kết quả health mong đợi có `status`, `postgres`, `qdrant` đều là `ok`.

### 3. Tạo dữ liệu mẫu

```powershell
docker compose exec api python -m scripts.seed_demo
```

Lệnh tạo 3 ứng viên, 5 recruiter và 5 chiến dịch demo. Có thể chạy lại mà không tạo dữ liệu trùng.

### 4. Tạo vector PhoBERT

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/api/v1/embeddings/recruiters/rebuild
Invoke-RestMethod -Method Post http://127.0.0.1:8001/api/v1/embeddings/campaigns/rebuild
```

Kết quả mong đợi là `embedded` lớn hơn `0`. Chỉ cần chạy lại khi thay đổi dữ liệu recruiter/chiến dịch hoặc đổi model embedding.

### 5. Chạy giao diện

Mở một cửa sổ PowerShell mới tại thư mục gốc dự án:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Mở trình duyệt tại `http://127.0.0.1:5173`, chọn tab **Ghép ứng viên**, chọn ứng viên rồi bấm **Tìm recruiter phù hợp**.

## Xem dữ liệu

### PostgreSQL qua pgAdmin/DBeaver

Tạo kết nối mới với các thông tin:

```text
Host: localhost
Port: 5433
Database: recruitment_ai
User: recruitment_user
Password: recruitment_dev_password
```

Các bảng chính: `candidates`, `recruiters`, `campaigns`, `recruiter_campaigns`, `model_versions`, `embedding_refs`.

Hoặc xem bằng terminal:

```powershell
cd matching_service
docker compose exec postgres psql -U recruitment_user -d recruitment_ai
```

```sql
\dt
SELECT * FROM candidates;
SELECT * FROM recruiters;
```

### Qdrant

Mở `http://localhost:6335/dashboard` rồi chọn **Collections**. Sau khi rebuild sẽ có collection vector cho recruiter và campaign.

## Vận hành Docker

| Việc cần làm | Lệnh |
| --- | --- |
| Xem trạng thái | `docker compose ps` |
| Xem log API | `docker compose logs -f api` |
| Dừng nhưng giữ dữ liệu | `docker compose down` |
| Khởi động lại | `docker compose up -d` |
| Xóa toàn bộ dữ liệu local | `docker compose down -v` |

Chỉ dùng `docker compose down -v` khi muốn xóa toàn bộ PostgreSQL/Qdrant local và làm lại từ đầu.

## Xử lý lỗi thường gặp

| Hiện tượng | Cách xử lý |
| --- | --- |
| API trả `EMBEDDING_MODEL_UNAVAILABLE` | Kiểm tra `.env` có `INSTALL_EMBEDDINGS=true`, sau đó chạy lại `docker compose up --build -d`. |
| API trả `500` | Xem chi tiết bằng `docker compose logs -f api`. |
| Không có kết quả ghép | Chạy seed và hai lệnh rebuild vector ở trên; sau đó tải lại trang Vue. |
| Cổng 5433 hoặc 6335 bị chiếm | Sửa `POSTGRES_HOST_PORT` hoặc `QDRANT_HOST_PORT` trong `matching_service/.env`, rồi chạy lại Docker. |
| PowerShell báo chặn `npm.ps1` | Dùng `npm.cmd` thay cho `npm`. |

## Tài liệu bổ sung

- [Hướng dẫn chuyển audio và Colab GPU](README_WEB.md)
- [Tài liệu API matching](matching_service/README.md)
- [Đặc tả giao diện matching](specs/006-hybrid-matching-ui/spec.md)
