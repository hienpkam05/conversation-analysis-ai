# API Contract: Đặc tả 001 - Nền tảng Matching

## Base URL

```text
http://localhost:8001/api/v1
```

## GET `/health`

Kiểm tra trạng thái API, PostgreSQL và Qdrant.

### Thành công

Status:

```text
200 OK
```

Response:

```json
{
  "status": "ok",
  "service": "candidate-recruiter-matching",
  "postgres": "ok",
  "qdrant": "ok"
}
```

### Lỗi dependency

Status:

```text
503 Service Unavailable
```

Response:

```json
{
  "status": "error",
  "service": "candidate-recruiter-matching",
  "postgres": "ok",
  "qdrant": "error",
  "detail": "Qdrant connection failed"
}
```

### Ghi chú

- Endpoint không được lộ credentials.
- Có thể thêm latency trong phase sau, nhưng Đặc tả 001 chưa bắt buộc.
- Endpoint này kiểm tra hạ tầng, chưa kiểm tra model AI.

## API tương lai

Các đặc tả sau sẽ thêm:

```text
POST /matching/candidates/{candidate_id}
GET  /matching/runs/{run_id}
POST /matching/runs/{run_id}/select/{recruiter_id}
POST /embeddings/recruiters/rebuild
POST /embeddings/campaigns/rebuild
```
