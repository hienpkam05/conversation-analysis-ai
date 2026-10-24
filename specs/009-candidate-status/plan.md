# Kế hoạch triển khai 009

## Kiến trúc

Django app candidate_status dùng Revision/Conversation và session/CSRF/phân quyền của 007. Vue có workspace riêng, dùng sự kiện đổi session chung để hủy cache riêng tư ở các tab. Không cần sửa matching FastAPI, PostgreSQL hay Qdrant.

## Bản đầu

1. Công bố bộ nhãn đề xuất và hợp đồng API trước khi xây luồng.
2. StatusDecision lưu snapshot bất biến; tạo bản sửa mới thay vì cập nhật nội dung gốc.
3. Gợi ý quy tắc chỉ từ lời ứng viên rõ ràng, có đường lui unknown, không xác suất giả.
4. Chặn xác nhận nguồn cũ/chưa kiểm tra; lưu người/thời điểm xác nhận và khóa revision.
5. Hiển thị lịch sử, dẫn chứng, bản thủ công và trạng thái đã xác nhận trên web.
6. Kiểm thử hồi quy backend và workflow trình duyệt trên fixture riêng; không xác nhận hộ 20 cuộc thật.

## Sau nghiệm thu

Chốt định nghĩa nhãn với nghiệp vụ, gán nhãn và duyệt độc lập. Sau đó chuẩn bị train/validation/test theo nhóm cuộc gọi/ứng viên để tránh rò rỉ. Chọn checkpoint ViDeBERTa đã kiểm tra giấy phép, huấn luyện và đánh giá macro-F1/confusion matrix cùng tỷ lệ chuyển unknown. Chưa có dữ liệu chuẩn thì không tự train hay gắn nhãn rules thành nhãn thật.
