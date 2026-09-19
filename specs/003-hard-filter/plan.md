# Kế hoạch triển khai: Đặc tả 003

1. Tạo repository candidate, recruiter, campaign.
2. Tạo `HardFilterService` độc lập với FastAPI.
3. Thêm endpoint kiểm tra eligibility.
4. Dùng `EXISTS` cho campaign active và eager loading để tránh N+1.
5. Test unit service và gọi endpoint bằng dữ liệu seed.
