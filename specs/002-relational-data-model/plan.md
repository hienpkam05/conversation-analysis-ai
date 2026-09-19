# Kế hoạch triển khai: Đặc tả 002

## Phases

1. Mở rộng settings cho pipeline hybrid bốn thành phần.
2. Tạo enum và SQLAlchemy models.
3. Viết migration `20260919_0001` với upgrade/downgrade.
4. Viết script seed demo bằng UUID ổn định.
5. Cập nhật README, Docker image và gitignore.
6. Áp migration, chạy seed lặp lại, kiểm tra số lượng dữ liệu và test.

## Quyết định

- `candidates.phone` unique nhưng không phục vụ scoring.
- Soft delete được đặt tại candidate, recruiter và campaign.
- `recruiter_regions` và `recruiter_campaigns` là bảng nối, không lưu mảng ID.
- JSON metadata dùng PostgreSQL JSONB.
- Mọi ID nghiệp vụ dùng UUID.
