# Chuẩn bị audio cho đánh giá chất lượng tư vấn

## Đợt mẫu đầu tiên

### Khảo sát ngày 2026-10-18

Đã đọc metadata bộ dữ liệu local người dùng chỉ định: 1.101 MP3, tổng thời lượng metadata khoảng 39,44 giờ, 1.100 file đọc được là mono 8 kHz và 1 file không mở được header. Chưa giải mã toàn bộ hoặc nghe để xác nhận chất lượng lời nói. Đã chọn 20 file theo các nhóm thời lượng, tổng khoảng 84,54 phút; đây là mẫu theo metadata, chưa phải mẫu phân loại tốt/xấu theo nội dung.

Danh mục local nằm ở `data/quality_dataset/inventory.csv`; thống kê ở `summary.json`; danh sách mẫu có đường dẫn audio gốc ở `pilot.json`. Các file này được Git ignore, audio gốc không bị sao chép hoặc thay đổi. Mono không cho phép phân vai bằng hai kênh; cần kiểm tra lời thoại/người nói trước khi gán nhãn.

Có thể tạo lại danh mục từ thư mục gốc dự án:

```powershell
venv\Scripts\python.exe backend\consultation_quality\inventory_audio.py "DUONG_DAN_THU_MUC_AUDIO" --output data/quality_dataset
```

Lệnh chỉ đọc header MP3 bằng PyAV hiện có, không chạy STT, không gọi Colab và không huấn luyện. Chuyển lời nói thành văn bản và chấm nhãn là các bước tiếp theo.

### Đợt STT pilot đã hoàn tất

Đã nhận dạng 20 mẫu bằng large-v3 local CPU: 19 transcript nháp và 1 mẫu chưa phát hiện lời nói, tổng 325 đoạn. Các vai trò vẫn chưa được xác nhận; chưa có nhãn điểm chất lượng tư vấn trên mẫu thật. 9 cuộc có 21 đoạn gắn cờ cần nghe kỹ, không tự xóa nội dung. Có thể chọn mẫu, nghe audio gốc sau reload, sửa transcript, xác nhận người nói, lưu nháp và gửi bản chấm chờ duyệt ngay trên tab Đánh giá tư vấn.

Bản đối chiếu ở `data/quality_dataset/review-transcripts.json` có đủ 20 mẫu, không xuất nhãn train hoặc đường dẫn audio gốc. Audio vẫn nằm tại thư mục nguồn; chuyển/xóa file nguồn sẽ khiến trình nghe lại báo không tìm thấy file.

Chuẩn bị khoảng 10–20 cuộc gọi có quyền sử dụng, gồm cuộc tư vấn tốt, thiếu thông tin, ứng viên hỏi nhiều, cuộc ngắn/bị ngắt và chất lượng ghi âm khác nhau. Đây là tập khảo sát và chốt cách chấm, chưa đủ để cam kết huấn luyện model tốt. Không yêu cầu một số lượng cố định cho toàn bộ tập train trước khi xem phân bố nhãn và kết quả pilot.

Có thể đặt file vào thư mục local `data/quality_audio/` và báo đường dẫn. Định dạng mp3, wav, m4a đều theo luồng nhận dạng hiện có. Mỗi cuộc đặt mã như `call_0001.m4a`, tránh dùng tên/số điện thoại làm tên file. Không đưa audio thật lên Git; thêm thư mục dữ liệu vào ignore trước khi đặt file.

Nếu biết kênh ghi âm hoặc vai trò, gửi kèm thông tin: mono/stereo, kênh trái/phải tương ứng với ai, bản ghi có đầy đủ từ đầu đến cuối hay bị cắt. Audio mono không tự bảo đảm phân biệt được người nói; trước mắt cần nghe và xác nhận thủ công.

## Luồng tạo nhãn trên web hiện tại

1. Ở tab Hội thoại, chọn audio và chuyển thành văn bản bằng Local hoặc Colab đang hoạt động.
2. Chuyển sang Đánh giá tư vấn, bấm Lấy hội thoại từ audio.
3. Nghe lại audio, sửa lỗi nhận dạng; tách/gộp các đoạn thành lượt nói, gán tư vấn viên/ứng viên.
4. Chọn tiêu chí đang chấm bằng radio, rồi chọn các ô Dẫn chứng bên lời thoại.
5. Chấm 0/1/2 hoặc ghi lý do Không đủ dữ liệu. Nếu hành vi không xuất hiện, chọn điểm 0, loại bằng chứng tương ứng, phạm vi đã xem và lời giải thích.
6. Lưu đánh giá thủ công. Mọi bản đang là nháp theo rubric đề xuất; chưa tự đưa vào train.

Audio trên màn chấm là file đã chọn trong phiên trình duyệt, không phải kho audio lâu dài. Khi tải lại trang cần chọn lại file nếu muốn nghe; lời thoại và bản chấm đã lưu vẫn mở lại được từ danh sách.

## Dữ liệu còn cần trước khi train

- Rubric được duyệt, mô tả rõ mức 0/1/2 và không đủ dữ liệu cho cả 5 tiêu chí.
- Transcript được sửa và xác nhận vai trò; chỉ đưa phần văn bản vào ViDeBERTa, audio dùng để đối chiếu.
- Hai người chấm độc lập một phần tập pilot và thống nhất cách giải quyết bất đồng.
- Nhãn đã duyệt, dẫn chứng và mã nhóm cuộc gọi/ứng viên để tránh rò rỉ giữa train/test.
- Xử lý thông tin nhận dạng trước khi xuất dữ liệu huấn luyện.

Audio đơn lẻ không chứa nhãn chất lượng tư vấn. Sau khi khảo sát đợt đầu, quyết định mở rộng số lượng theo độ đa dạng dữ liệu, phân bố nhãn, bất đồng người chấm và đường cong học của model.
