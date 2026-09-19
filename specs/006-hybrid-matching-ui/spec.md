# Đặc tả 006: Hybrid Matching và Giao diện sử dụng

## Mục tiêu

Biến hạ tầng matching thành luồng người dùng có thể sử dụng: chọn ứng viên, nhận Top-K recruiter, xem điểm thành phần và lý do gợi ý trên Vue frontend.

## Pipeline

```text
Candidate
-> PostgreSQL hard filter
-> PhoBERT encode candidate profile
-> Qdrant recruiter retrieval (Top-N, eligible IDs only)
-> Qdrant campaign fit
-> rerank semantic/campaign/performance/workload
-> Top-K + reasons
```

## Điểm số

```text
final = 0.55 * semantic
      + 0.20 * campaign_fit
      + 0.15 * performance
      + 0.10 * workload
```

Mọi component nằm trong `[0, 1]`. Tie-break: final score giảm dần, semantic giảm dần, workload giảm dần, recruiter ID tăng dần.

## API

```text
GET  /api/v1/candidates
POST /api/v1/matching/candidates/{candidate_id}
```

## Frontend

Vue có tab `Ghép ứng viên` trong ứng dụng hiện tại. Người dùng chỉ chọn candidate và nhấn nút matching; Docker/Qdrant/SWAGGER không nằm trong luồng thao tác hàng ngày.

## Ngoài phạm vi

- Chưa persist `matching_runs`/`matching_results`: Spec 007.
- Chưa có thao tác chọn recruiter và khóa workload transactionally: Spec 008.
