# Nhật ký chạy Quickstart - 2026-08-17

## Mục đích

Ghi lại kết quả kiểm tra thủ công sau khi triển khai Đặc tả 001.

## Môi trường

- OS: Windows
- Workspace: `D:\NCKH`
- API port: `8001`
- PostgreSQL port: `5432`
- Qdrant port: `6333`

## Lệnh cần chạy sau khi triển khai xong

```bash
cd matching_service
docker compose up --build
```

```bash
curl http://localhost:8001/api/v1/health
```

```bash
alembic current
```

```bash
pytest
```

## Kết quả

Chưa chạy. Hiện tại mới viết đặc tả.

## Ghi chú

Nếu máy chưa có Docker Desktop, ghi blocker tại đây trước khi bắt đầu triển khai.
