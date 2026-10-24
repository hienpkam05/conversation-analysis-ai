# Công việc 010: Thông tin và chiến dịch

## A. Bản dùng được

- [x] T001 Định nghĩa trường, thiếu/mâu thuẫn và dẫn chứng Unicode span trong hợp đồng API.
- [x] T002 CandidateProfile/CampaignSearch snapshot và migration; tái sử dụng quyền/session/CSRF của 007.
- [x] T003 Trích xuất quy tắc bảo thủ từ ứng viên, tách nơi ở/nơi muốn làm, lương tháng và ngày tương đối không tự đoán.
- [x] T004 Bản manual, giải quyết xung đột, xác nhận đúng nguồn/version và lịch sử bất biến.
- [x] T005 API chiến dịch đọc PostgreSQL/Qdrant, lọc active/vùng/lương tùy chọn, kiểm ref/hash/point/version.
- [x] T006 Gửi query tối thiểu có xác nhận; kiểm response và lỗi HTTP; không tự tạo hồ sơ/gán chiến dịch.
- [x] T007 Tab Vue có đối chiếu nguồn, sửa/xác nhận, kết quả và lịch sử; cache theo session.
- [x] T008 Backend/matching tests và trình duyệt desktop/mobile, HTTP thành công/503/HTML qua Postman simulation tách biệt.

## B. Nghiệm thu và mô hình NER

- [ ] T009 Người phụ trách nghiệm thu schema/trích xuất trên audio thật, rà nhầm người nói/ý định và thông tin riêng tư.
- [ ] T010 Gán nhãn span/BIO, duyệt độc lập, chia tập theo ứng viên/chuỗi liên hệ và đánh giá dữ liệu.
- [ ] T011 Chọn/check license checkpoint, train PhoBERT NER và đo precision/recall/F1 từng loại thực thể.
- [ ] T012 Tích hợp/kiểm chứng checkpoint NER thật và thử end-to-end với dữ liệu đã duyệt.
- [ ] T013 Chuẩn hóa địa điểm/ca/ngày bắt đầu chiến dịch nếu muốn có bộ lọc có cấu trúc đầy đủ.
- [ ] T014 Tạo hồ sơ PostgreSQL hoặc gắn chiến dịch bằng xác nhận riêng nếu người dùng yêu cầu.

Nguồn trích xuất hiện là rules/manual, không đánh dấu phần train hoàn tất. Chi tiết bằng chứng kiểm thử và thử runtime thật nằm ở quickstart-run-2026-10-23.md.
