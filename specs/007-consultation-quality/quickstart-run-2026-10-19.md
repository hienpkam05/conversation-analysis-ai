# Biên bản bổ sung hướng dẫn chấm ngày 2026-10-19

## Đã thực hiện

- Viết ANNOTATION_GUIDE.md và phiếu trống PILOT_REVIEW.md cho đợt thử ba cuộc gọi; mọi ví dụ điểm là giả định.
- Bổ sung định nghĩa chi tiết cho năm tiêu chí trong `backend/consultation_quality/rubric.py`, version quality-draft-v2, status=draft, trọng số đề xuất bằng nhau.
- Hiển thị quy tắc chung, mức điểm, trường hợp không đủ dữ liệu, ranh giới và ví dụ trên Vue. Hiển thị mã bản chấm/transcript để đối chiếu khi chấm kép.
- Giữ snapshot cũ, từ chối gửi điểm bằng version cũ và không tự chuyển điểm cũ vào form version mới.

## Kiểm tra

- Django: 19 tests qua, có regression test rubric v1 không bị sửa khi tạo bản chấm v2 và submission v1 bị từ chối.
- Vite production build: qua.
- Không phát sinh migration mới.
- Edge headless: mở hướng dẫn cho mẫu thật call_0387, kiểm tra đủ năm phần mức điểm/ví dụ; ảnh desktop và mobile 390×844 không tràn ngang, không có lỗi JavaScript.
- Trình duyệt mô phỏng response lịch sử v1 chỉ để kiểm tra form: điểm cũ không tự điền sang v2. Không ghi fixture đó vào database.
- Kết quả/ảnh kiểm tra local trong `data/quality_dataset/guide-browser-result.json`, `guide-desktop.png`, `guide-mobile.png`; được Git ignore.

## Chưa thực hiện

Chưa có người chấm thực hiện pilot theo hướng dẫn mới, chưa giải quyết bất đồng hoặc duyệt rubric. Không tạo điểm cho audio thật và không train. T001/T003/P011 vẫn chờ công việc nghiệp vụ thực tế; việc viết hướng dẫn không thay thế các bước này.
