# Đặc tả 001: Nền tảng Matching ứng viên - Nhân viên tuyển dụng

## Trạng thái

Bản nháp để thống nhất phạm vi trước khi code.

## Mục tiêu

Tạo nền kỹ thuật ban đầu cho một service riêng phục vụ bài toán **Matching ứng viên với nhân viên tuyển dụng**.

Service này về sau sẽ đề xuất **Top 3 nhân viên tuyển dụng phù hợp nhất** cho một ứng viên bằng pipeline:

1. Lọc điều kiện cứng từ PostgreSQL
2. Truy hồi ngữ nghĩa bằng Qdrant
3. Chấm điểm lại bằng độ phù hợp chiến dịch, workload và hiệu suất

Đặc tả 001 chỉ dựng nền. Chưa triển khai thuật toán matching.

## Bối cảnh

Dự án hiện tại đã có app Django/Vue để upload audio và chuyển hội thoại thành văn bản. File `Bai_toan_1.docx` mô tả một kiến trúc backend riêng cho bài toán Candidate-Recruiter Matching:

- Backend: FastAPI
- CSDL nghiệp vụ: PostgreSQL
- Vector database: Qdrant
- ORM/migration: SQLAlchemy 2.x async + Alembic
- Tầng AI: embedding provider có thể thay thế

Để tránh trộn trách nhiệm, phần matching nên được tách thành một service riêng.

## Phạm vi làm trong đặc tả này

- Tạo thư mục `matching_service/`
- Tạo khung app FastAPI
- Tạo lớp cấu hình/settings
- Tạo logging cơ bản
- Tạo async SQLAlchemy database session
- Cấu hình Alembic
- Tạo Docker Compose gồm:
  - API
  - PostgreSQL
  - Qdrant
- Tạo health endpoint kiểm tra:
  - API sống
  - PostgreSQL kết nối được
  - Qdrant kết nối được
- Tạo `.env.example`
- Tạo README hướng dẫn chạy local
- Tạo test tối thiểu cho health endpoint

## Không làm trong đặc tả này

- Chưa tạo schema bảng candidate/recruiter/campaign
- Chưa seed dữ liệu ứng viên/nhân viên/chiến dịch
- Chưa triển khai embedding provider
- Chưa tạo Qdrant collection thật cho embeddings
- Chưa làm hard filter
- Chưa làm thuật toán matching/reranking
- Chưa trả Top 3 recruiter
- Chưa làm endpoint xác nhận chọn recruiter
- Chưa làm offline evaluation
- Chưa nối với app Django/Vue hiện tại

## Câu chuyện người dùng

### Câu chuyện 1: Developer khởi động service matching

Là developer, tôi muốn chạy một lệnh để khởi động PostgreSQL, Qdrant và FastAPI local, để các phase sau có môi trường ổn định.

Tiêu chí chấp nhận:

- `docker compose up --build` khởi động được các service.
- API truy cập được tại `http://localhost:8001`.

### Câu chuyện 2: Developer kiểm tra các phụ thuộc

Là developer, tôi muốn có endpoint health kiểm tra PostgreSQL và Qdrant, để biết lỗi setup ngay từ đầu.

Tiêu chí chấp nhận:

- `GET /api/v1/health` trả `200` khi API, PostgreSQL và Qdrant đều kết nối được.
- Trả `503` nếu PostgreSQL hoặc Qdrant không sẵn sàng.

### Câu chuyện 3: Developer chạy được migration

Là developer, tôi muốn Alembic được cấu hình từ đầu, để các thay đổi schema sau này có kiểm soát.

Tiêu chí chấp nhận:

- `alembic current` chạy được.
- `alembic upgrade head` chạy được trên database rỗng.

## Yêu cầu chức năng

### FR-001: Cấu trúc service

Phần triển khai phải tạo service mới tại:

```text
matching_service/
```

Không đặt logic matching vào Django `backend/` hiện tại.

### FR-002: API prefix

API dùng prefix:

```text
/api/v1
```

### FR-003: Health endpoint

Service phải có:

```text
GET /api/v1/health
```

Response thành công:

```json
{
  "status": "ok",
  "service": "candidate-recruiter-matching",
  "postgres": "ok",
  "qdrant": "ok"
}
```

Response khi lỗi:

```json
{
  "status": "error",
  "service": "candidate-recruiter-matching",
  "postgres": "ok",
  "qdrant": "error",
  "detail": "..."
}
```

### FR-004: Cấu hình

Service đọc cấu hình từ biến môi trường bằng `pydantic-settings`.

Cần có cấu hình cho:

- Tên app / môi trường chạy
- API prefix
- Database URL
- Qdrant URL / API key
- Matching top K
- Retrieval top N
- Trọng số scoring

### FR-005: Docker Compose

`matching_service/docker-compose.yml` phải có:

- `postgres`
- `qdrant`
- `api`

API bind ra host port `8001` để không đụng Django backend hiện tại ở port `8000`.

### FR-006: Alembic

Alembic phải được cấu hình với metadata của SQLAlchemy.

Đặc tả 001 có thể chưa có bảng nghiệp vụ, nhưng migration framework phải sẵn sàng cho đặc tả 002.

## Yêu cầu phi chức năng

### NFR-001: Tách biệt trách nhiệm

Matching service phải độc lập với app transcription.

### NFR-002: Tái lập môi trường

Mọi giá trị cấu hình mặc định phải được ghi trong `.env.example`.

### NFR-003: Có thể kiểm thử

Health endpoint phải có test tự động.

### NFR-004: An toàn port

Port API mặc định là `8001`.

## Tiêu chí hoàn thành

- Có thư mục `matching_service/` với khung FastAPI.
- `docker compose up --build` khởi động API, PostgreSQL và Qdrant.
- `GET http://localhost:8001/api/v1/health` trả trạng thái phụ thuộc.
- `alembic current` chạy được.
- Có `.env.example`.
- README giải thích setup, migration và test.
- Test tối thiểu chạy pass.

## Câu hỏi còn mở

1. Máy triển khai có Docker Desktop không?
2. Port `8001` có ổn không?
3. PostgreSQL host port giữ `5432` hay đổi `5433` để tránh đụng máy local?
4. Qdrant host port giữ `6333` hay đổi port khác nếu máy đã có Qdrant?
