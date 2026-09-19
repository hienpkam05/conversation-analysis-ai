# Quickstart: Đặc tả 002

```powershell
cd D:\NCKH\matching_service
docker compose up --build -d
docker compose exec api alembic upgrade head
docker compose exec api python -m scripts.seed_demo
```

Kiểm tra revision:

```powershell
docker compose exec api alembic current
```

Kiểm tra số lượng demo:

```powershell
docker compose exec postgres psql -U recruitment_user -d recruitment_ai -c "SELECT count(*) FROM recruiters;"
```
