# Biên bản chuẩn bị D ngày 2026-10-19

## Dữ liệu thật

Lệnh quality_training_status chạy trên SQLite Django hiện tại trả 0 assessment, 0 approved_manual; rubric quality-draft-v2 vẫn draft; giữ nguyên 20 mẫu audio. Chưa nhận đường dẫn tập nhãn ngoài database. Không tự duyệt hoặc dùng transcript làm nhãn.

Lệnh thử export:

```powershell
venv\Scripts\python.exe -X utf8 backend\manage.py export_quality_training data/quality_dataset/training/approved-v1.json --rubric-version quality-draft-v2
```

Kết quả: exit 1, CommandError rubric chưa được người phụ trách duyệt đầy đủ. Không tạo artifact train rỗng. Đây là cổng kiểm tra hoạt động đúng, không phải đã huấn luyện thành công.

## Code đã triển khai

- Export manual approved có người chấm/duyệt, kiểm tra revision mới nhất, dẫn chứng/rubric/tổng, loại NA toàn bộ hoặc nhãn mâu thuẫn, tôn trọng bản thay thế/kết luận pilot.
- Che định danh và ánh xạ ID, không xuất nhận xét/metadata/đường dẫn gốc. Checksum và xác nhận người rà riêng tư trước chia tập; regex không được coi là ẩn danh hoàn chỉnh.
- Group split trước windowing, gộp nhóm ứng viên/nội dung trùng; seed cố định, ba tập độc lập không rỗng, label distribution và cảnh báo thiếu lớp. Không tự khẳng định phát hiện được trùng ngữ nghĩa.
- Baseline majority train-only, macro-F1 không gian ba lớp, confusion matrix, support/mask NA, MAE tiêu chí/tổng và trạng thái luôn cần duyệt.
- Các artifact không được ghi đè, release_approved=false. Không thêm dependency lớn hoặc thay đổi schema/database.

## Kiểm thử

Chạy `venv\Scripts\python.exe -X utf8 backend\manage.py test consultation_quality --noinput`.

47 tests gồm 31 kiểm thử A/B và 16 kiểm thử dữ liệu/metric/baseline. Fixture có dữ liệu tổng hợp trong database test riêng và file tạm được dọn sau test; không ghi nhãn tổng hợp vào database thật. Kiểm thử command export → split → baseline thực sự ghi/đọc artifact tạm, kiểm tra mask/lỗi/chống ghi đè và không dùng validation/test để fit baseline.

Kiểm tra migration không có thay đổi. Chưa chạy báo cáo trên nhãn thật; chưa tải tokenizer/checkpoint, train ViDeBERTa, đo tài nguyên hay chốt ngưỡng phát hành. T017–T020 và E vẫn mở.

## Việc cần từ người dùng

Cung cấp đường dẫn nhãn nếu đã có ngoài Django. Nếu chưa gán nhãn, hoàn tất luồng A trên ba cuộc pilot, duyệt rubric rồi mở rộng nhãn có đối chiếu. Hướng dẫn và câu lệnh tại TRAINING.md.
