# Quickstart: Đặc tả 001 - Nền tảng Matching

Quickstart này mô tả cách chạy phần triển khai tương lai của Đặc tả 001.

## 1. Vào thư mục service

```bash
cd matching_service
```

## 2. Tạo file môi trường

```bash
cp .env.example .env
```

Trên Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

## 3. Khởi động services

```bash
docker compose up --build
```

Các service dự kiến:

- API: `http://localhost:8001`
- PostgreSQL: `localhost:5433` (tránh trùng PostgreSQL local ở `5432`)
- Qdrant: `http://localhost:6335` (tránh trùng Qdrant local ở `6333`)

## 4. Kiểm tra health

```bash
curl http://localhost:8001/api/v1/health
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

## 5. Chạy Alembic

```bash
alembic current
```

## 6. Chạy test

```bash
pytest
```

## Xử lý lỗi thường gặp

### API port bị chiếm

Đổi host port `8001` trong `docker-compose.yml`.

### PostgreSQL port bị chiếm

Đổi mapping:

```text
5432:5432
```

thành:

```text
5433:5432
```

### Qdrant port bị chiếm

Đổi mapping:

```text
6333:6333
```

sang port còn trống, rồi cập nhật `.env`.
