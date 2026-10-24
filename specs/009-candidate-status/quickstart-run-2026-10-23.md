# Kết quả chạy ngày 23/10/2026

## Môi trường và bảo toàn dữ liệu

- Django local với SQLite; đã áp dụng candidate_status.0001_initial.
- Đã tạo bản sao SQLite trước migration tại data/quality_dataset/backups/before-status-2026-10-23.sqlite3 (Git bỏ qua).
- Backend 127.0.0.1:8002, Vite 127.0.0.1:5175 qua cấu hình frontend/.env.local có sẵn.
- Giữ nguyên 20 audio, 20 revision và ba tài khoản nguoi_duyet/nguoi_cham_a/nguoi_cham_b.
- Browser test tạo tài khoản/hội thoại/nhãn fixture riêng và xóa sau khi chạy. Không xác nhận trạng thái cho dữ liệu thật. Sau kiểm thử có 0 StatusDecision, 0 user/hội thoại QA009.

## Kết quả kỹ thuật

- `manage.py test consultation_quality conversation_followup candidate_status --noinput`: **102 tests đạt**, gồm 19 tests mới.
- `manage.py makemigrations --check --dry-run`: không có thay đổi thiếu migration.
- `npm.cmd run build`: đạt.
- `git diff --check`: không lỗi whitespace; chỉ có cảnh báo LF/CRLF.
- Playwright/Edge headless: desktop 1440x1000 và mobile 390x844.
- Đăng nhập sai hiển thị lỗi, đăng nhập đúng mở workspace: đạt.
- Tạo gợi ý, lưu bản sửa thủ công có dẫn chứng, bắt buộc checkbox đối chiếu trước xác nhận: đạt.
- Reload giữ trạng thái đã xác nhận; tạo draft mới không thay trạng thái confirmed: đạt.
- Đăng xuất xóa cache nội dung của tab đánh giá tư vấn đã mở: đạt.
- Mobile không tràn ngang: viewport=390, body.scrollWidth=390. Không có lỗi JavaScript trong luồng chạy.
- Đã xem ảnh desktop/mobile, sửa màu chữ nhãn để đủ tương phản. Artifacts ở data/quality_dataset/status-desktop.png, status-mobile.png và status-browser-result.json (không đưa lên Git).

## Giới hạn

Chưa chạy ViDeBERTa, chưa huấn luyện hoặc đo chất lượng phân loại trên cuộc gọi thật. Bộ nhãn vẫn là đề xuất và cần nghiệm thu. Gợi ý quy tắc không hiểu đầy đủ ngữ cảnh và có thể bỏ sót/sai; phải đối chiếu trước xác nhận. Kết quả kiểm thử kỹ thuật không phải chỉ số chất lượng mô hình.
