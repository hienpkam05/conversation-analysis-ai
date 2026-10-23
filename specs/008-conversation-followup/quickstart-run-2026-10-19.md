# Kết quả kiểm thử ngày 19/10/2026

## Môi trường

- Django local, SQLite; migration conversation_followup.0001_initial đã áp dụng.
- Django 127.0.0.1:8002; Vue 127.0.0.1:5175 qua proxy cấu hình .env.local.
- Edge headless qua Playwright, desktop 1440x1000 và mobile 390x844.
- Tài khoản/hội thoại/lịch kiểm thử riêng được xóa sau khi chạy; không dùng mật khẩu tài khoản thật.

## Kết quả

- 83 kiểm thử Django consultation_quality và conversation_followup đạt (15 kiểm thử mới cho 008).
- Tạo bản trích dẫn, mở nguồn, tạo bản sửa thủ công, lưu và duyệt: đạt.
- Không tự tạo lịch khi tạo tóm tắt: đạt.
- Lưu lịch nháp, bắt buộc xác nhận người tham gia, xác nhận lịch: đạt.
- Reload vẫn thấy lịch đã xác nhận, hủy lịch và lưu lịch sử: đạt.
- Đăng xuất trong tab tóm tắt xóa cache hội thoại ở tab đánh giá: đạt.
- Mobile không tràn ngang: viewport 390, body.scrollWidth 390.
- Không ghi nhận lỗi JavaScript trong luồng kiểm thử.
- Đã xem ảnh desktop và mobile; ảnh/JSON kiểm thử nằm trong data/quality_dataset, được Git bỏ qua.

## Chưa nghiệm thu

Đây là baseline trích dẫn theo quy tắc, không phải mT5 đã train. Chưa đo chất lượng tóm tắt trên audio thật, chưa được người dùng nghiệm thu nghiệp vụ, chưa gửi lịch đến calendar/email/SMS. Không dùng kết quả kiểm thử kỹ thuật thay cho đánh giá chất lượng nội dung thực tế.
