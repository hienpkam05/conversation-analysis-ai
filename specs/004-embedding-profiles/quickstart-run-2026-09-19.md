# Kết quả chạy Spec 004 - 2026-09-19

## Đã xác nhận

- `pytest -q`: 14 test pass.
- API health: PostgreSQL và Qdrant đều `ok`.
- Seed demo đã đồng bộ `model_versions` thành:
  - `model_name`: `vinai/phobert-base-v2`
  - `version`: `meanpool-v1`
  - `dimension`: `768`

## Chưa chạy trong môi trường hiện tại

- Tải PhoBERT và gọi `encode()` thật. Đây là dependency tùy chọn vì cần tải PyTorch, Transformers và checkpoint model lần đầu.

Lệnh cần chạy khi sẵn sàng tải model:

```powershell
cd matching_service
pip install -e ".[embeddings,dev]"
```
