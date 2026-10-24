# Công việc 009: Trạng thái ứng viên

## A. Bản dùng được

- [x] T001 Định nghĩa 5 trạng thái đề xuất và unknown, phạm vi không tự quyết định tuyển dụng.
- [x] T002 Hợp đồng API và snapshot StatusDecision bất biến, migration và audit xác nhận.
- [x] T003 Gợi ý quy tắc dựa trên lời ứng viên có dẫn chứng, không phần trăm giả.
- [x] T004 Nhãn thủ công riêng, lịch sử, stale/version guard, kiểm tra vai/transcript và quyền xác nhận.
- [x] T005 Tab Vue chọn hội thoại, nghe nguồn, chọn dẫn chứng, lưu/xác nhận và xem lại trạng thái hiện hành.
- [x] T006 Backend tests quyền/CSRF/bằng chứng/phủ định/mâu thuẫn/snapshot và hồi quy 007/008.
- [x] T007 Kiểm thử trình duyệt desktop/mobile, lưu/mở lại, giữ trạng thái confirmed khi có draft mới, xóa cache đăng xuất.

## B. Nghiệm thu và mô hình thật

### Công cụ đã triển khai

- [x] B001 Phê duyệt định nghĩa bộ nhãn có hash/audit trên web, không tự duyệt khi migrate.
- [x] B002 Duyệt nhãn manual độc lập, từ chối tự duyệt/rules/model, giữ audit bất biến.
- [x] B003 Báo cáo tiến độ/phân bố/bất đồng và exporter chỉ nhận nhãn đủ điều kiện.
- [x] B004 Che thông tin, xác nhận riêng tư bằng SHA256, chia nhóm và gộp bản trùng để chống rò rỉ.
- [x] B005 Script train ViDeBERTa local, chọn epoch/ngưỡng trên validation và báo cáo test/baseline; chưa chạy model thật.
- [x] B006 Provider model local có manifest/checksum, kiểm tra phê duyệt, giới hạn cửa sổ/concurrency và nút AI khóa khi thiếu model.
- [x] B007 Lệnh duyệt checkpoint, tài liệu môi trường/nguồn/giới hạn và kiểm thử kỹ thuật không cần model giả.

### Điều kiện thực tế còn chờ

- [ ] T008 Người phụ trách duyệt định nghĩa nhãn và nghiệm thu trên transcript/audio thật.
- [ ] T009 Gán nhãn và duyệt dữ liệu; thống kê support, bất đồng và chia tập theo nhóm.
- [ ] T010 Chọn/check license checkpoint ViDeBERTa, chuẩn bị môi trường và script huấn luyện.
- [ ] T011 Train, đo macro-F1/confusion matrix, hiệu chỉnh ngưỡng chuyển unknown và đánh giá lỗi nghiệp vụ.
- [ ] T012 Tích hợp provider model có phiên bản, giới hạn tài nguyên và nghiệm thu trước khi dùng.

T009 đã có công cụ xuất/chia/duyệt, T010 đã có script và checkpoint tham chiếu, T012 đã có provider; các mục vẫn mở vì chưa có dữ liệu/model thật và chưa nghiệm thu. Xem [TRAINING.md](TRAINING.md). Không đổi trạng thái các mục này chỉ vì test fixture đã qua.

Hoàn thành A không có nghĩa đã hoàn thành mô hình AI. Không tạo/xác nhận nhãn thật thay người dùng.
