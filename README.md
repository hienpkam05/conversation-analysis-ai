# AI Recruitment Lab

Ứng dụng hỗ trợ tuyển dụng lao động tạm thời gồm các chức năng:

- Chuyển file ghi âm tư vấn tuyển dụng thành văn bản.
- Ghép ứng viên với recruiter phù hợp dựa trên điều kiện nghiệp vụ, PhoBERT và Qdrant.
- Chấm thủ công chất lượng tư vấn và quản lý nhãn có duyệt.
- Tóm tắt trích dẫn hội thoại, sửa/duyệt nội dung và xác nhận lịch hẹn nội bộ.

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

### Đánh giá chất lượng tư vấn bản local

Chức năng chấm thủ công chạy qua Django, không dùng API matching. Khởi động Django bằng môi trường Python đã cài dependency:

```powershell
venv\Scripts\python.exe backend\manage.py migrate
venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
```

Chạy Vue như bước 5 rồi chọn **Đánh giá tư vấn**. Nhập văn bản hoặc chuyển audio ở tab Hội thoại và bấm **Lấy hội thoại từ audio** trong tab đánh giá. Kiểm tra người nói, chọn tiêu chí và lời thoại dẫn chứng, chấm điểm rồi lưu. Dữ liệu lưu trong SQLite của Django (`backend/db.sqlite3`), không phải PostgreSQL matching. Danh sách hội thoại cho phép mở lại các bản đã lưu.

Bộ tiêu chí hiện vẫn chờ duyệt nghiệp vụ thật; đã có đăng nhập, phân quyền, quản lý rubric, chấm kép và duyệt nhãn. Trước khi mở tab, tạo tài khoản bằng `venv\Scripts\python.exe -X utf8 backend\manage.py quality_user nguoi_duyet --reviewer --assign-pilot`. Mật khẩu nhập ẩn, không có giá trị mặc định. Hai tài khoản người chấm và luồng pilot được hướng dẫn tại [quickstart.md](specs/007-consultation-quality/quickstart.md). Chưa có model ViDeBERTa fine-tune hoặc tự train. Đây là môi trường localhost, không phải cấu hình phát hành Internet. Dữ liệu/audio/database cá nhân không được đưa lên Git.

Trước khi chấm hàng loạt, đọc [hướng dẫn gán nhãn](specs/007-consultation-quality/ANNOTATION_GUIDE.md) và [phiếu chấm thử](specs/007-consultation-quality/PILOT_REVIEW.md). Trên web có mức điểm/ví dụ của quality-draft-v2 để tra ngay; tiêu chí và nhãn vẫn cần người phụ trách duyệt trước khi train.

Khung Chấm AI đã có hàng đợi/tiến độ/worker và bản sửa thủ công riêng, nhưng chưa có checkpoint chất lượng tư vấn thật. Thiếu model thì hệ thống khóa gửi và không tạo điểm. Cách cấu hình runtime sau khi có model đã duyệt: [AI_RUNTIME.md](specs/007-consultation-quality/AI_RUNTIME.md). Chuẩn bị nhãn và baseline: [TRAINING.md](specs/007-consultation-quality/TRAINING.md). Database matching trên Docker không mặc nhiên chứa nhãn chất lượng tư vấn.

### Tóm tắt và lịch hẹn

Chọn tab **Tóm tắt & lịch hẹn**, dùng chung tài khoản và hội thoại của phần đánh giá tư vấn. Bản đầu chọn trích dẫn theo quy tắc và giữ dẫn chứng nguồn, chưa dùng model mT5 đã train. Transcript/vai người nói cần được kiểm tra trước khi duyệt tóm tắt. Lịch phải có ngày giờ cụ thể và xác nhận của người dùng; không tự gửi calendar/email/SMS. Xem [hướng dẫn Spec 008](specs/008-conversation-followup/quickstart.md), gồm cấu hình local Django 8002/Vue 5175 khi cổng 8000 bị chiếm.

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
