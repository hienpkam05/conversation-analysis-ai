# Nghiên cứu và quyết định 007

## Những gì đã biết

- Theo ảnh tài liệu người dùng cung cấp: bài toán 2 dùng ViDeBERTa Multi-task, dùng chung encoder và 5 đầu đánh giá.
- File Word hiện có tập trung vào matching; chưa có định nghĩa 5 tiêu chí chất lượng tư vấn.
- Dự án đã có Vue, Django STT, FastAPI matching và Qdrant. Trang STT nhận JSON; chưa có workflow sửa vai trò và lưu hội thoại cho đánh giá.

## Quyết định thiết kế đề xuất

1. Làm gán nhãn/chấm thủ công trước để có đầu ra dùng được và dữ liệu huấn luyện.
2. Đề xuất rubric 5 tiêu chí theo spec, giữ trạng thái nháp đến khi được duyệt.
3. Dùng Django cho module hội thoại, tái sử dụng frontend hiện có; không thêm vector database cho đánh giá chất lượng.
4. Tách score, confidence, khả năng đánh giá và trạng thái duyệt. Không biến softmax thành lời cam kết đúng/sai.
5. Giữ phiên bản hội thoại và rubric bất biến để dẫn chứng có thể kiểm tra lại.
6. Phân loại văn bản không đo được âm điệu, ngắt lời hay tốc độ nói. Các yếu tố đó chỉ thêm sau nếu có nguồn audio và phương pháp kiểm chứng.
7. ViDeBERTa phân loại không tự giải thích bằng chứng. Giai đoạn đầu người chấm chọn dẫn chứng; AI chưa có dẫn chứng kiểm chứng được luôn cần duyệt.

## Thí nghiệm cần thực hiện

- Thử gán nhãn kép trên tập pilot, ghi bất đồng theo từng tiêu chí rồi sửa hướng dẫn trước khi mở rộng.
- Đo baseline đơn giản trước khi so sánh ViDeBERTa; dùng cùng tập test và cùng rubric.
- So sánh phương án chia cửa sổ/kết hợp dự đoán, kiểm tra tình huống hành vi chỉ xuất hiện ở cuối cuộc gọi.
- Theo dõi mất cân bằng nhãn, lỗi STT và tỷ lệ vai trò chưa xác định.
- Đo thời gian, RAM/VRAM thực tế; con số RAM trong ảnh là ước lượng định hướng, không phải cam kết tài nguyên.

## Nội dung chưa xác minh

Chưa chọn checkpoint/model hub cụ thể, chưa kiểm tra giấy phép, chưa có tập dữ liệu hoặc số đo F1. Tài liệu này không tuyên bố đã fine-tune hay đạt chất lượng nào. Khi triển khai ML cần ghi nguồn chính thức và tái lập kết quả trước khi quyết định phát hành.
