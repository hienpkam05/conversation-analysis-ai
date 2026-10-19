# Kế hoạch 007

## Vị trí trong hệ thống

Đặt module `consultation_quality` trong Django vì đây là luồng xử lý hội thoại, dùng proxy `/api` hiện có. Vue bổ sung tab đánh giá tư vấn. FastAPI matching và Qdrant tiếp tục phụ trách bài toán 1. Không tạo thêm microservice cho giai đoạn đầu.

Module dùng database Django đã cấu hình; không mặc định các bảng của nó nằm trong PostgreSQL matching ở cổng 5433. Trước khi triển khai cần kiểm tra `DATABASES`, migration và yêu cầu lưu trữ để chọn SQLite phát triển hoặc PostgreSQL cho môi trường dùng chung. Không tự tạo liên kết recruiter giữa hai database.

## Các giai đoạn

1. Xác nhận rubric với người phụ trách, xây hướng dẫn gán nhãn và chấm thử một tập nhỏ để xử lý bất đồng.
2. Tạo models/migrations, lưu phiên bản hội thoại và rubric; validation nghiệp vụ trong service Django.
3. Tạo API nhập/sửa nháp, đóng phiên bản, lưu đánh giá thủ công, xem lại lịch sử.
4. Thêm tab Vue và chuyển kết quả STT sang nháp đánh giá. Kiểm tra đủ workflow thủ công trước khi phụ thuộc model.
5. Chuẩn bị dữ liệu, ẩn thông tin nhận dạng khi xuất tập huấn luyện; chia train/validation/test theo nhóm.
6. Chốt checkpoint, baseline và phương án cửa sổ hội thoại; fine-tune model 5 đầu, lưu cấu hình và báo cáo đánh giá.
7. Thêm provider model tải lười, tiến trình xử lý nền có giới hạn, trả trạng thái job cho giao diện. Không chạy tải model trong request web kéo dài.
8. Thử nghiệm AI có người duyệt; chỉ phát hành khi đáp ứng cổng nghiệm thu trong spec.

## Kiểm thử

- Unit: tính tổng, validation bằng chứng, vai trò, không đủ dữ liệu và tổng trọng số.
- Integration: migration mới, version bất biến, lưu đánh giá, job thất bại/model thiếu, quyền truy cập.
- Model: tách nhóm không rò rỉ, bao phủ transcript dài, mask nhãn thiếu, cố định version khi suy luận.
- Frontend: luồng nhập/chỉnh vai trò/chấm/lưu/mở lại; trạng thái job và lỗi; build Vue và kiểm tra desktop/mobile.

## Điều kiện triển khai

Ưu tiên hoàn tất giai đoạn A trước. Trong lúc chưa có dữ liệu nhãn, giao diện vẫn hữu ích để tạo chính dữ liệu phục vụ giai đoạn B. Các endpoint mới được xây theo hợp đồng trong `contracts/api.md`; đây là thiết kế, chưa phải API đang chạy.
