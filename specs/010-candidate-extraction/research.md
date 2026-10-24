# Quyết định và giới hạn

- Không có PhoBERT NER đã huấn luyện trong dự án. Bản đầu dùng regex/cụm từ tường minh, có nguồn, thiếu/mâu thuẫn và bản sửa thủ công. Không có % confidence giả hoặc gọi quy tắc là model NER.
- Tiền xử lý NER không tự sửa lời nguồn. Vị trí dẫn chứng theo Unicode code point; giao diện tạo span toàn lượt dùng Array.from để không nhầm UTF-16 khi có emoji.
- Chỉ nhận số điện thoại 10 chữ số sau chuẩn hóa +84; số bàn/ASR đọc số bằng chữ cần người sửa. Lương tự chuẩn hóa chỉ khi có đơn vị triệu/tháng rõ; khoảng lương, VND dạng khác hoặc thiếu kỳ lương cần đối chiếu. Giữ ngày tương đối ở dạng văn bản, không đoán lịch.
- Không tự ánh xạ địa danh sang danh mục hành chính/vùng. Nơi ở và nơi muốn làm là hai trường riêng.
- Matching dùng lại provider/version hiện có; chưa thay embedding bằng NER. Vector hết hạn/profile đổi bị loại thay vì coi là mới. Điểm cosine không phải xác suất nhận việc.
- API tìm chỉ đọc dữ liệu; muốn tạo hồ sơ hoặc gắn chiến dịch cần bước nghiệp vụ riêng sau này, tránh bản trích xuất sai ghi đè PostgreSQL.
- Chỉ gửi thông tin nghề nghiệp đã xác nhận, không gửi các trường định danh/full transcript. Có che cơ bản cả định danh lẫn số/email/URL nằm trong text, nhưng regex không bảo đảm ẩn danh hoàn chỉnh; người dùng cần kiểm tra phần văn bản nghề nghiệp trước khi gửi, đặc biệt khi cấu hình service ngoài localhost.
- HTTP có timeout kết nối/đọc 3.05/30 giây, không redirect, không đọc proxy từ môi trường và cap response 512 KB. Đây không phải hard deadline toàn tác vụ model ở upstream. Mô phỏng chỉ dùng dữ liệu giả tách biệt, không dùng làm nhãn hoặc chiến dịch thật.
- Khi thiếu model/vector/database, trả lỗi; không chạy fallback cosine giả hoặc tự rebuild trong search request. Huấn luyện NER và nghiệm thu dữ liệu thật vẫn còn chờ.
