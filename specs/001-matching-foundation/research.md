# Nghiên cứu: Đặc tả 001 - Nền tảng Matching

## Tài liệu nguồn

- `Bai_toan_1.docx`
- Trạng thái repository hiện tại:
  - Đã có app Django/Vue để transcribe audio
  - Đã có luồng Colab GPU để xử lý ASR nặng

## Ý chính từ `Bai_toan_1.docx`

Backend matching được đặc tả là một service FastAPI riêng, dùng:

- PostgreSQL cho dữ liệu nghiệp vụ
- Qdrant cho vector retrieval
- SQLAlchemy 2.x async + Alembic
- Embedding provider có thể thay thế

Pipeline matching mong muốn:

```text
Candidate
-> Profile Builder
-> PostgreSQL Hard Filter
-> Embedding
-> Qdrant Semantic Retrieval
-> Re-ranking
-> Top 3 recruiter + lý do
-> Human confirm/reject
```

## Vì sao Đặc tả 001 chưa làm matching

Hệ thống matching đầy đủ cần nền ổn định trước:

- Ranh giới service rõ
- Kết nối database ổn
- Kết nối Qdrant ổn
- Migration workflow có từ đầu
- Config validate được
- Có test harness

Nếu nhảy vào matching ngay, các phần schema/model/config sau này sẽ dễ bị trộn và khó sửa.

## Quyết định kiến trúc

Tạo service riêng:

```text
matching_service/
```

Không đưa logic matching vào Django `backend/`.

Lý do:

- Tài liệu NCKH chọn FastAPI.
- Matching là bounded context khác với audio transcription.
- Các thí nghiệm về model/config cần tái lập được.

## Quyết định port

Dùng:

```text
8001
```

Lý do:

- Django backend hiện tại dùng `8000`.
- Matching service cần chạy song song với app transcription.

## Chiến lược dependency

Đặc tả 001 chưa cài các dependency ML nặng như:

- `torch`
- `transformers`
- `sentence-transformers`

Lý do:

- Nền service có thể kiểm tra nhanh.
- Embedding provider thuộc phase sau.

## Rủi ro còn mở

### Docker Desktop

Phần triển khai giả định máy có Docker Desktop.

Nếu không có Docker:

- Chạy PostgreSQL riêng
- Chạy Qdrant riêng
- Chạy FastAPI trực tiếp bằng Python local

### Trùng port PostgreSQL

Port mặc định `5432` có thể trùng PostgreSQL local.

Fallback:

```text
5433:5432
```

### Trùng port Qdrant

Port mặc định `6333` có thể trùng Qdrant local.

Fallback:

- Đổi host port
- Cập nhật `.env`
