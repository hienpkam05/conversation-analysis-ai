# Quickstart: Đặc tả 003

Sau khi migration và seed Spec 002 đã chạy:

```powershell
cd D:\NCKH\matching_service
docker compose up --build -d
```

Lấy ID candidate test:

```powershell
docker compose exec postgres psql -U recruitment_user -d recruitment_ai -c "SELECT id, province FROM candidates;"
```

Gọi endpoint bằng ID nhận được:

```powershell
Invoke-RestMethod http://localhost:8001/api/v1/candidates/PUT_CANDIDATE_ID_HERE/eligible-recruiters
```
