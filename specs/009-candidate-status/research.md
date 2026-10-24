# Quyết định và giới hạn

- Dùng Django/SQLite và Vue hiện có, không thêm thư viện hoặc dịch vụ cho bản đầu.
- Quy tắc cụm từ minh bạch giúp thử luồng và thu thập nhãn; không thay cho mô hình hiểu hội thoại. Không có kết quả đo độ chính xác trên dữ liệu thật.
- Chỉ dùng lời ứng viên, không suy trạng thái từ đánh giá chủ quan của tư vấn viên hoặc thông tin cá nhân nhạy cảm.
- Khi nhiều nhãn khớp hoặc phát hiện câu điều kiện/phủ định/mơ hồ thì chọn unknown. Không chọn từ khóa cuối cùng làm quyết định cuối.
- Có thể bỏ sót nhiều cách nói tự nhiên, phương ngữ, lời đồng ý cần ngữ cảnh; người dùng sửa thủ công. Quy tắc không bảo đảm nhận diện hết trích dẫn/ý mỉa mai/phủ định lồng nhau.
- Gợi ý bước tiếp theo chỉ là văn bản tham khảo. Không tự hủy hồ sơ, từ chối tuyển dụng, tạo lịch hoặc liên hệ người khác.
- ViDeBERTa là hướng tiếp theo, chưa chọn/download checkpoint hoặc suy luận model trong bản này. Tài liệu 007/MODEL_SELECTION.md không chứng minh một checkpoint có sẵn phù hợp nhiệm vụ trạng thái.
- Trạng thái được người tạo xác nhận chỉ là dữ liệu nghiệp vụ. Trước khi dùng làm nhãn train cần quy trình gán nhãn/duyệt và kiểm tra phân bố lớp riêng, tránh lấy gợi ý rules tự xác nhận làm nhãn vàng.
