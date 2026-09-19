# Chạy Spec 006

## Matching API

```powershell
cd matching_service
docker compose up --build -d
Invoke-RestMethod http://localhost:8001/api/v1/candidates
```

Muốn nhận Top-K thật, hoàn tất rebuild vector ở Spec 005 trước.

## Frontend

```powershell
cd frontend
npm.cmd run dev
```

Mở `http://127.0.0.1:5173`, chọn tab `Ghép ứng viên`, chọn candidate và nhấn `Tìm recruiter phù hợp`.
