# Công việc: Đặc tả 001 - Nền tảng Matching

## Chú thích trạng thái

- `[ ]` Chưa làm
- `[~]` Đang làm
- `[x]` Đã xong

## P1: Khung project

- [x] Tạo thư mục `matching_service/`
- [x] Tạo entrypoint FastAPI
- [x] Tạo API v1 router
- [x] Thêm `GET /api/v1/health`
- [x] Thêm Pydantic settings
- [x] Thêm logging config

## P2: Dependencies

- [x] Tạo `pyproject.toml`
- [x] Thêm dependency FastAPI
- [x] Thêm dependency SQLAlchemy async
- [x] Thêm dependency Alembic
- [x] Thêm dependency Qdrant client
- [x] Thêm dependency pytest

## P3: Docker

- [x] Tạo `Dockerfile`
- [x] Tạo `docker-compose.yml`
- [x] Thêm service PostgreSQL
- [x] Thêm service Qdrant
- [x] Thêm service API
- [x] Expose API ở port `8001`

## P4: Môi trường cấu hình

- [x] Tạo `.env.example`
- [x] Cấu hình `APP_ENV`
- [x] Cấu hình `DATABASE_URL`
- [x] Cấu hình `QDRANT_URL`
- [x] Cấu hình trọng số matching
- [x] Validate tổng trọng số

## P5: Nền database

- [x] Tạo SQLAlchemy async engine
- [x] Tạo async session factory
- [x] Tạo declarative base
- [x] Tạo package models rỗng

## P6: Alembic

- [x] Tạo `alembic.ini`
- [x] Tạo `alembic/env.py`
- [x] Trỏ Alembic vào SQLAlchemy metadata
- [x] Xác nhận `alembic current` chạy được

## P7: Health checks

- [x] Kiểm tra PostgreSQL bằng `SELECT 1`
- [x] Kiểm tra Qdrant bằng client health/collections call
- [x] Trả 200 khi cả hai dependency hoạt động
- [x] Trả 503 khi có dependency lỗi

## P8: Tests

- [x] Thêm test health endpoint
- [x] Thêm test validate config
- [x] Thêm test trường hợp dependency lỗi nếu khả thi

## P9: Tài liệu

- [x] Tạo `matching_service/README.md`
- [x] Ghi hướng dẫn setup
- [x] Ghi lệnh Docker
- [x] Ghi lệnh migration
- [x] Ghi lệnh test

## P10: Kiểm tra cuối

- [x] Chạy format/lint nếu có cấu hình
- [x] Chạy tests
- [x] Chạy Docker Compose
- [x] Gọi health endpoint
- [x] Ghi lại rủi ro còn lại
