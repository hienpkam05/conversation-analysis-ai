# Kế hoạch 008

1. Dùng app Django conversation_followup, cùng database quality. Summary giữ revision hash và snapshot; Appointment/Audit giữ lịch sử.
2. Tái sử dụng session/CSRF/visible_conversations và quyền hiện có. Chủ bản ghi hoặc review_quality được sửa/duyệt; người được giao hội thoại có quyền đọc và tạo bản riêng.
3. Baseline chọn nguyên văn theo từ khóa và vai trò, không tải dependency/model mới. Mỗi ý luôn có ID nguồn; không suy ra việc đồng ý từ nội dung trích.
4. Duyệt khóa revision, kiểm tra phiên bản mới nhất trong transaction; thay transcript phải tạo tóm tắt mới. Bản tự động chỉ sửa bằng copy manual.
5. Lịch draft có request_key; sửa có version; confirm có cờ người dùng và dữ liệu đầy đủ. Khóa tài khoản chủ lịch để kiểm tra trùng giờ nội bộ.
6. Tab Vue độc lập Tóm tắt & lịch hẹn, nghe audio, sửa tóm tắt, lịch nháp/duyệt/hủy. Xóa cache hai workspace khi session thay đổi.
7. Unit/integration + trình duyệt với fixture riêng; giữ nguyên 20 audio và các tài khoản người dùng đã tạo.

Không mở inference mT5 khi chưa có checkpoint; không gọi API ngoài hay dùng dữ liệu 007 nháp làm nhãn train.
