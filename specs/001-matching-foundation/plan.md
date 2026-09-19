# Kế hoạch triển khai: Đặc tả 001 - Nền tảng Matching

## Mục tiêu

Tạo nền FastAPI độc lập cho service matching, để về sau có thể thêm PostgreSQL hard filter, Qdrant semantic retrieval và re-ranking.

## Quyết định kỹ thuật

| Hạng mục | Quyết định |
| --- | --- |
| Vị trí service | `matching_service/` |
| Framework | FastAPI |
| Port API | `8001` |
| Database nghiệp vụ | PostgreSQL |
| Vector database | Qdrant |
| ORM | SQLAlchemy 2.x async |
| Migration | Alembic |
| Config | Pydantic Settings |
| Test | Pytest |

## Cây thư mục mục tiêu

```text
matching_service/
  app/
    __init__.py
    main.py
    api/
      __init__.py
      v1/
        __init__.py
        health.py
    core/
      __init__.py
      config.py
      logging.py
    db/
      __init__.py
      base.py
      session.py
      models/
        __init__.py
    schemas/
      __init__.py
      health.py
    services/
      __init__.py
      health_service.py
  alembic/
    env.py
    script.py.mako
    versions/
  tests/
    test_health.py
  alembic.ini
  Dockerfile
  docker-compose.yml
  .env.example
  pyproject.toml
  README.md
```

## Các phase triển khai

### Phase 1: Khung project

Tạo thư mục, FastAPI app, router API và config.

Kết quả cần có:

- `app/main.py`
- `app/core/config.py`
- `app/api/v1/health.py`

### Phase 2: Hạ tầng chạy local

Thêm Dockerfile và Docker Compose.

Kết quả cần có:

- `Dockerfile`
- `docker-compose.yml`
- `.env.example`

### Phase 3: Kết nối PostgreSQL và Qdrant

Thêm SQLAlchemy async session và service kiểm tra Qdrant.

Kết quả cần có:

- `app/db/session.py`
- `app/services/health_service.py`

### Phase 4: Alembic

Cấu hình Alembic để dùng metadata của SQLAlchemy.

Kết quả cần có:

- `alembic.ini`
- `alembic/env.py`

### Phase 5: Test và tài liệu

Thêm test health endpoint và README.

Kết quả cần có:

- `tests/test_health.py`
- `README.md`

## Lệnh kiểm tra

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

## Rủi ro

- Máy có thể chưa cài Docker Desktop.
- Port có thể bị trùng với service local khác.
- Qdrant có thể khởi động chậm hơn API.
- Cấu hình async SQLAlchemy + Alembic cần làm cẩn thận.

## Đặc tả tiếp theo

Đặc tả 002 sẽ thêm schema database, migration và seed data cho candidates, recruiters, campaigns, model_versions, embedding_refs, matching_runs và matching_results.
