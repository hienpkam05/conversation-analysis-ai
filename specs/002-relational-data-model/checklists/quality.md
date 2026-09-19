# Checklist chất lượng: Đặc tả 002

- [x] Có migration upgrade/downgrade.
- [x] Có foreign key, check constraint và index cần thiết.
- [x] Có soft delete cho entity nghiệp vụ chính.
- [x] Phone được giữ trong PostgreSQL và không có thiết kế ghi PII vào Qdrant.
- [x] Seed dùng UUID ổn định và idempotent.
- [x] Seed tạo tối thiểu 5 recruiter, 5 campaign, 3 candidate.
- [x] Config kiểm tra weight và retrieval top N.
