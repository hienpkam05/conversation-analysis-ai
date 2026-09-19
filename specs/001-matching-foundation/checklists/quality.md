# Checklist chất lượng: Đặc tả 001 - Nền tảng Matching

## Cấu trúc

- [ ] Code matching nằm trong `matching_service/`
- [ ] Không thêm logic matching vào app Django/Vue transcription hiện tại
- [ ] API code được tách lớp router/service/config/db

## Config

- [ ] Có `.env.example`
- [ ] Không commit `.env` thật
- [ ] Settings được load bằng Pydantic Settings
- [ ] Trọng số matching được validate

## Runtime

- [ ] API chạy ở port `8001`
- [ ] PostgreSQL chạy bằng Docker Compose
- [ ] Qdrant chạy bằng Docker Compose
- [ ] Health endpoint kiểm tra PostgreSQL
- [ ] Health endpoint kiểm tra Qdrant

## Database

- [ ] Có SQLAlchemy async engine
- [ ] Có session factory
- [ ] Có declarative base
- [ ] Alembic được khởi tạo
- [ ] `alembic current` chạy được

## Tests

- [ ] Có test health thành công
- [ ] Trường hợp dependency lỗi được test hoặc ghi rõ cách kiểm tra thủ công
- [ ] Chạy test bằng `pytest`

## Tài liệu

- [ ] README giải thích setup local
- [ ] README giải thích Docker Compose
- [ ] README giải thích migration
- [ ] README giải thích test

## Điều kiện hoàn thành

- [ ] `docker compose up --build` chạy được
- [ ] `GET /api/v1/health` trả JSON đúng
- [ ] Tests pass
- [ ] Không commit file sinh tự động/cache
