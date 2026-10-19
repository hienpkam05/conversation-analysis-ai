# Phiếu chấm thử và duyệt bộ tiêu chí

Mẫu trống dùng với annotation-guide-2026-10-19 / quality-draft-v2. Sao chép phiếu điền vào `data/quality_dataset/annotations/` nếu có lời thoại thật hoặc thông tin người chấm; thư mục dữ liệu local được Git ignore. Không ghi kết quả giả vào phiếu mẫu này.

## Chuẩn bị đợt thử

| Mục | Thông tin cần điền |
| --- | --- |
| Người phụ trách duyệt rubric | Chưa xác định |
| Người chấm A/B | Chưa xác định; dùng mã để ghi nhận |
| Rubric | quality-draft-v2, đang nháp |
| Ngày chấm | Chưa chấm |
| Mẫu đề xuất | call_0387, call_0994, call_1066 |
| Nghe/sửa transcript trước chấm | Chưa thực hiện |

## Phiếu từng cuộc

Lặp lại phần này cho từng mã cuộc gọi và từng người chấm. Điền mã bản chấm/transcript từ lịch sử trên web; không dùng hai revision khác nhau để so độ thống nhất.

- Mã cuộc gọi: ...
- Người chấm: A/B/...
- Mục đích chính: tư vấn công việc / xác nhận lịch / theo dõi / khác: ...
- Bản ghi đủ đầu/cuối và nghe rõ: ...
- Mã revision transcript: ...
- Mã bản chấm: ...
- Các sửa transcript/role cần lưu ý: ...

| Tiêu chí | Điểm 0/1/2 hoặc Không đủ dữ liệu | Lượt dẫn chứng/phạm vi đã xem | Lý do |
| --- | --- | --- | --- |
| Mở đầu | Chưa chấm | Chưa chọn | Chưa ghi |
| Khai thác nhu cầu | Chưa chấm | Chưa chọn | Chưa ghi |
| Thông tin công việc | Chưa chấm | Chưa chọn | Chưa ghi |
| Lắng nghe và giải đáp | Chưa chấm | Chưa chọn | Chưa ghi |
| Bước tiếp theo | Chưa chấm | Chưa chọn | Chưa ghi |

Tổng điểm: chưa có. Trạng thái: chưa gán nhãn, chưa duyệt, không dùng train.

## Bảng xử lý bất đồng

| Cuộc/tiêu chí | Điểm A | Điểm B | Cùng revision? | Nguồn bất đồng | Quyết định và lý do | Ai xác nhận? |
| --- | --- | --- | --- | --- | --- | --- |
| Chưa có kết quả | — | — | Chưa kiểm tra | Chưa xác định | Chưa quyết định | Chưa có |

Nguồn bất đồng có thể là nghe sai, sai vai, thiếu ngữ cảnh, định nghĩa mức điểm hoặc phạm vi áp dụng. Không tự lấy trung bình điểm để giải quyết.

## Quyết định sau pilot

- [ ] Đã nghe, sửa và thống nhất revision cho các cuộc thử.
- [ ] Đã chấm độc lập và ghi nhận các bất đồng thực tế.
- [ ] Đã chốt cách xử lý bản ghi ngắn/cắt, ứng viên từ chối và cuộc chỉ xác nhận lịch.
- [ ] Người phụ trách đã duyệt định nghĩa 0/1/2/Không đủ dữ liệu và trọng số.
- [ ] Đã ghi người duyệt, ngày duyệt và phiên bản được duyệt.

Quyết định hiện tại: **chưa có**. Việc tạo phiếu không phê duyệt rubric, không phê duyệt nhãn và không chạy huấn luyện.
