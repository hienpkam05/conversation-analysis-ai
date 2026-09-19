# Đặc tả 002: Schema dữ liệu Matching và Seed demo

## Mục tiêu

Tạo relational schema cho Candidate-Recruiter Matching trong PostgreSQL, quản lý bằng Alembic và có dữ liệu demo lặp lại an toàn. Đây là nền dữ liệu để các đặc tả sau làm hard filter, embedding, Qdrant retrieval và re-ranking.

## Phạm vi

- SQLAlchemy model cho candidate, recruiter, campaign và quan hệ.
- Alembic migration tạo và rollback schema.
- Ràng buộc dữ liệu, foreign key và index phục vụ truy vấn sau này.
- Seed idempotent: 5 recruiter, 5 campaign, 3 candidate, 1 model version.
- Cập nhật config scoring bốn thành phần, kiểm tra tổng trọng số và `RETRIEVAL_TOP_N >= MATCHING_TOP_K`.
- Unit test cho config và metadata schema.

## Ngoài phạm vi

- Chưa có endpoint CRUD.
- Chưa có profile builder hoặc embedding provider.
- Chưa tạo Qdrant collection hay ghi vector.
- Chưa có hard filter, Top 3, matching run/result thực tế hay thao tác chọn recruiter.

## Tiêu chí chấp nhận

- `alembic upgrade head` tạo 9 bảng matching trên PostgreSQL rỗng.
- `alembic current` hiển thị revision `20260919_0001`.
- Seed có thể chạy nhiều lần mà không tạo thêm bản ghi.
- Schema có constraint workload, conversion rate, salary range và unique key cần thiết.
- Bảng `matching_results` chặn trùng recruiter/rank trong cùng một run.
- PII chỉ nằm ở PostgreSQL; chưa có logic ghi PII vào Qdrant.
