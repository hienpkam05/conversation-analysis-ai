# Chạy Spec 005

## Cài dependency embedding

```powershell
cd matching_service
pip install -e ".[embeddings,dev]"
```

Nếu chạy trong Docker, đặt `INSTALL_EMBEDDINGS=true` trong `.env`, rồi rebuild image:

```powershell
docker compose up --build -d
```

Image mặc định giữ nhẹ với `INSTALL_EMBEDDINGS=false`; endpoint rebuild sẽ trả `503 EMBEDDING_MODEL_UNAVAILABLE` cho tới khi extra ML được cài.

Dockerfile dùng PyTorch CPU-only khi bật cờ này, tránh tải bộ CUDA/NVIDIA không cần thiết cho môi trường local CPU.

## Rebuild

```powershell
python -m scripts.rebuild_embeddings recruiters
python -m scripts.rebuild_embeddings campaigns
```

Hoặc gọi API:

```powershell
Invoke-RestMethod -Method Post http://localhost:8001/api/v1/embeddings/recruiters/rebuild
Invoke-RestMethod -Method Post http://localhost:8001/api/v1/embeddings/campaigns/rebuild
```

Kết quả trả `total`, `embedded`, `skipped`, collection name và model version ID. Chạy lại không có thay đổi phải cho `embedded=0`.
