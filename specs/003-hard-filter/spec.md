# Đặc tả 003: Hard Filter recruiter

## Mục tiêu

Tạo lớp lọc recruiter đủ điều kiện bằng PostgreSQL trước semantic retrieval. Đây là business constraint bắt buộc, không phải một phần của điểm AI.

## Quy tắc

- Recruiter phải `active` và chưa soft-delete.
- Recruiter phải còn capacity: `current_workload < max_workload`.
- Khi `STRICT_REGION=true`, recruiter phải cùng region và thuộc tỉnh của candidate hoặc phụ trách toàn region.
- Khi `REQUIRE_ACTIVE_CAMPAIGN=true`, recruiter phải có ít nhất một liên kết campaign active với campaign đang active.

## Ngoài phạm vi

- Chưa gọi Qdrant hay PhoBERT.
- Chưa tính semantic score, campaign fit, workload score hoặc Top 3.
- Chưa tăng workload hay phân công recruiter.

## Endpoint kiểm tra

```text
GET /api/v1/candidates/{candidate_id}/eligible-recruiters
```

Trả recruiter đủ điều kiện và metadata workload, vùng, campaign. Candidate không tồn tại trả `404`; candidate thiếu region khi strict mode trả `422`.
