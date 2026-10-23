# Spec 008: Tóm tắt hội thoại và lịch hẹn

Ngày tạo: 2026-10-19. Phạm vi bản đầu: tóm tắt trích dẫn có dẫn chứng, sửa/duyệt thủ công và lịch hẹn nội bộ có xác nhận. Không coi đây là model tóm tắt đã fine-tune.

## Mục tiêu

Giúp người tư vấn xem nhanh nhu cầu, thông tin công việc, câu hỏi và lời nhắc về bước tiếp theo từ hội thoại; lập lịch rõ ràng sau khi người dùng đối chiếu với người tham gia. Tái sử dụng Conversation/Revision/audio/tài khoản của 007, không phụ thuộc nhãn chất lượng tư vấn hoặc PostgreSQL matching.

## Luồng

1. Đăng nhập, chọn hội thoại và revision đã lưu. Có thể xem bản trích dẫn nháp khi transcript chưa được kiểm tra; hiển thị trạng thái chưa đối chiếu.
2. Tạo bản trích chọn theo quy tắc có phiên bản. Mỗi ý tự động là nguyên văn một lượt, giữ ID nguồn và snapshot. Các từ như hẹn/phỏng vấn/gọi lại không được hiểu là đã đồng ý hoặc có lịch chính thức.
3. Tạo bản sửa thủ công riêng, sửa ý và chọn dẫn chứng. Không ghi đè bản trích dẫn hoặc bản đã duyệt.
4. Đối chiếu nội dung và duyệt tóm tắt. Cần revision mới nhất, nội dung/hash còn khớp, transcript và vai trò được kiểm tra; duyệt sẽ khóa revision. Duyệt tóm tắt không phải duyệt nhãn 007.
5. Nhập lịch nháp: tiêu đề, người tham gia, người phụ trách, hình thức, địa điểm/kênh, giờ bắt đầu/kết thúc cụ thể. Ngày tương đối trong lời thoại không được chuyển tự động sang ngày hệ thống.
6. Chọn lời đối chiếu từ cả ứng viên và tư vấn viên, xác nhận đã thống nhất với người tham gia rồi xác nhận lịch. Lịch thiếu dữ liệu/ở quá khứ/trùng giờ do cùng tài khoản tạo bị chặn.
7. Lưu lịch sử tạo/sửa/xác nhận/hủy. Lịch đã xác nhận không sửa tại chỗ; hủy và lập lịch mới. Không gửi email/SMS hay đồng bộ Google Calendar trong bản đầu.

## Yêu cầu nghiệm thu

- AC01: Xem tóm tắt từ hội thoại có quyền, mỗi ý có dẫn chứng đúng snapshot; không tạo dữ kiện ngoài lời thoại ở chế độ trích dẫn.
- AC02: Sửa thủ công và xem lại được; bảo toàn bản gốc và phiên bản đã duyệt. Sửa nháp có expected_version chống ghi đè.
- AC03: Transcript thay đổi làm bản cũ stale; không duyệt hoặc xác nhận lịch từ bản stale.
- AC04: Không tạo lịch xác nhận chỉ vì câu có từ “hẹn”, “mai”, “phỏng vấn” hoặc ứng viên từ chối. Tạo nháp và xác nhận là hai thao tác riêng.
- AC05: Ngày giờ có múi giờ, thời lượng >0 và <=8 giờ; lúc xác nhận phải còn ở tương lai. Tất cả giao diện hiển thị giờ Việt Nam.
- AC06: Xác nhận cần nội dung đã duyệt, người tham gia/phụ trách/kênh rõ ràng, dẫn chứng hai vai và thao tác xác nhận của người có quyền. Đây là xác nhận của người vận hành, không phải mô hình kiểm chứng đồng thuận.
- AC07: Không tạo trùng khi gửi lại request_key; không ghi đè lịch đã xác nhận, audit đúng actor/time; hủy không tự gửi thông báo ngoài.
- AC08: Phân quyền, CSRF, JSON lỗi, desktop/mobile và đăng xuất/đổi tài khoản không lộ cache của tab khác.

## Giới hạn

Rule-based extractive là baseline chạy local, không phải mT5/ViT5. Giới hạn tối đa ba trích dẫn/mục theo đầu/giữa/cuối, ghi số câu bỏ bớt; không hứa tóm tắt đầy đủ ngữ nghĩa. Tóm tắt trừu tượng bằng model, đánh giá factuality, chuẩn hóa ngày tự nhiên, lịch ngoài, thông báo và đồng bộ recruiter thuộc đợt sau, cần dữ liệu/nghiệm thu riêng.
