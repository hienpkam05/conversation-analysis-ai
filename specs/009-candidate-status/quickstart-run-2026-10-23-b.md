# Kết quả triển khai phần B ngày 23/10/2026

## Đã làm

- Phê duyệt định nghĩa bộ nhãn với SHA256/audit, không tự duyệt khi migrate.
- Duyệt nhãn thủ công độc lập, chặn tự duyệt, bản rules/model và nguồn stale/chưa kiểm tra. Audit không ghi đè; sửa bằng bản mới.
- Báo cáo tiến độ, support và lý do loại. Chặn nhãn đã duyệt mâu thuẫn hoặc còn bản manual mâu thuẫn chờ duyệt.
- Export nhãn đủ điều kiện, che thông tin cơ bản, xác nhận riêng tư và chia train/validation/test theo nhóm/thành phần liên thông của nhóm và bản trùng.
- Script train ViDeBERTa local; chọn epoch/ngưỡng trên validation, đánh giá test với baseline fit train, macro-F1/confusion matrix/support/unknown rate.
- Manifest/file checksum, lệnh duyệt checkpoint và provider local trên web; khóa khi thiếu model/dependency/phê duyệt, không tự dùng rules thay cho AI.

## Kiểm thử kỹ thuật

- 121 tests Django consultation_quality/conversation_followup/candidate_status đạt, gồm 19 tests phần B mới.
- Build Vue đạt; makemigrations --check không có thay đổi thiếu migration; diff --check không lỗi whitespace.
- Playwright/Edge: luồng A cũ tiếp tục đạt.
- Luồng B chạy trên SQLite **tách biệt** .cache/status-b-browser.sqlite3, API test 8003; không phê duyệt bộ nhãn trên database thật để thử UI.
- Gán/xác nhận bằng tài khoản annotator, đổi tài khoản reviewer, duyệt taxonomy, duyệt nhãn độc lập, báo cáo 1 nhãn fixture đủ điều kiện: đạt.
- Nút ViDeBERTa khóa khi chưa cấu hình checkpoint: đạt.
- Desktop 1440x1000, mobile 390x844, body.scrollWidth=390; không có lỗi JavaScript trong workflow. Đã xem ảnh.
- Fixture/tài khoản/audit trong database tách biệt đã được dọn sau kiểm thử. Ảnh và JSON nằm ở data/quality_dataset/status-b-*, Git bỏ qua.

Các tests provider/model output/release dùng mock hoặc file fixture để thử guard, **không phải chạy trọng số ViDeBERTa**. Không dùng các report fixture này để train/phát hành model thật.

## Database thật và điểm còn chờ

- Đã backup trước phần B: data/quality_dataset/backups/before-status-b-2026-10-23.sqlite3.
- Migrate 0002 và 0003 chỉ thêm schema; không thêm nhãn/phê duyệt giả.
- Sau kiểm thử: 20 audio, 20 revision, giữ ba tài khoản nguoi_duyet/nguoi_cham_a/nguoi_cham_b; 0 decision, 0 taxonomy approval, 0 label review, 0 transcript được xác nhận kiểm tra.
- `status_training status`: taxonomy_approved=false, eligible=0, unreviewed_transcripts=20.
- Môi trường hiện chưa có torch/transformers/safetensors/sentencepiece. Chưa cài ML hoặc tải checkpoint vì chưa có nhãn chuẩn và giấy phép trọng số còn cần kiểm tra.
- Chưa train thật, chưa đo F1/RAM/VRAM hoặc hiệu chỉnh/kiểm chứng model thật. T008–T012 vẫn mở ở phần nghiệm thu/dữ liệu/model, không đánh dấu xong chỉ vì đã có code.

## Tiếp theo cho người dùng

Mở http://127.0.0.1:5175 → Trạng thái ứng viên. Người phụ trách đọc/duyệt bộ nhãn khi đã thống nhất. Người chấm kiểm tra transcript/vai/audio usable, gán bản manual và xác nhận; người phụ trách khác tác giả duyệt nhãn train. Đọc ANNOTATION_GUIDE.md và TRAINING.md trước khi xuất hoặc đưa dữ liệu lên môi trường GPU.
