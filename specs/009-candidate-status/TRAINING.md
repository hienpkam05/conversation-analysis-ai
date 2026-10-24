# Chuẩn bị dữ liệu, train và dùng model trạng thái

## 1. Điều kiện thật còn thiếu

Ngày triển khai phần B: database Django có 20 transcript chưa được xác nhận kiểm tra, 0 nhãn trạng thái và bộ nhãn chưa duyệt. Không có tập train hoặc checkpoint trạng thái được tạo. Các lệnh dưới đây chỉ chạy tiếp khi bạn hoàn thành gán/duyệt dữ liệu thật theo [hướng dẫn gán nhãn](ANNOTATION_GUIDE.md).

Không dùng audio trực tiếp để fine-tune bộ phân loại văn bản. Audio dùng để đối chiếu transcript và nhãn; không dùng output quy tắc làm nhãn chuẩn tự động.

## 2. Kiểm tra tiến độ

```powershell
venv\Scripts\python.exe -X utf8 backend\manage.py status_training status
```

Hoặc mở Bộ nhãn và dữ liệu huấn luyện trên tab Trạng thái ứng viên bằng tài khoản reviewer. Có duyệt bộ nhãn, số nhãn đủ điều kiện, phân bố lớp và số transcript chưa kiểm tra. Không tự bấm duyệt khi chưa đối chiếu nghiệp vụ.

## 3. Xuất bản cần kiểm tra riêng tư

Chuẩn bị data/quality_dataset/status-groups.json, ánh xạ UUID hội thoại thật sang mã nhóm ứng viên/chuỗi liên hệ đã kiểm tra. Ví dụ minh họa, phải thay UUID bằng dữ liệu thật:

```json
{
  "UUID_HOI_THOAI_1": "nhom-lien-he-001",
  "UUID_HOI_THOAI_2_CUNG_NGUOI": "nhom-lien-he-001"
}
```

Chuẩn bị status-redact-terms.json là array tên/địa chỉ/thông tin cần che thêm. Ví dụ: `["Tên cần che", "Địa chỉ cần che"]`. Danh sách này ở local, không đưa lên Git.

```powershell
venv\Scripts\python.exe -X utf8 backend\manage.py status_training export --group-map data/quality_dataset/status-groups.json --redact-terms data/quality_dataset/status-redact-terms.json --output data/quality_dataset/status-export.json
```

Exporter chỉ nhận bản manual đã được người khác duyệt, nguồn mới nhất, audio usable và không có nhãn mâu thuẫn đang chờ xử lý. Che số điện thoại/email/URL/định danh bằng regex và các cụm bạn cung cấp; đây chưa bảo đảm ẩn danh đầy đủ. Đọc lại file, không tự upload dữ liệu tuyển dụng lên dịch vụ khác.

## 4. Chia train/validation/test

Sau khi đọc kiểm tra riêng tư thật, lấy dataset_sha256 trong file export:

```powershell
venv\Scripts\python.exe -X utf8 backend\manage.py status_training split --input data/quality_dataset/status-export.json --privacy-sha256 SHA256_DA_KIEM_TRA --reviewer TEN_NGUOI_KIEM_TRA --output data/quality_dataset/status-bundle.json
```

Tỷ lệ mục tiêu 70/15/15 theo nhóm, seed=42. Gộp nhóm liên hệ và transcript trùng sau che thông tin theo thành phần liên thông. Ít nhất 3 nhóm độc lập; tỷ lệ thực tế có thể khác. Bundle có support từng lớp và cảnh báo thiếu lớp; tối thiểu 3 nhóm không có nghĩa đủ dữ liệu cho mô hình tốt.

## 5. Môi trường ML riêng

Dùng Python 3.12 và môi trường riêng để không làm thay đổi môi trường web hiện tại:

```powershell
py -3.12 -m venv .venv-status-ml
.venv-status-ml\Scripts\python.exe -m pip install -r backend/candidate_status/requirements-ml.txt
```

Không cần cài ML để gán/duyệt nhãn. Bản cài PyTorch/CUDA cần phù hợp máy train; chưa đo RAM/VRAM thực tế. Có thể dùng máy GPU/Colab sau khi bạn kiểm tra quyền sử dụng dữ liệu; không tự gửi audio hoặc transcript lên Colab.

Đọc [nguồn checkpoint và giới hạn giấy phép](MODEL_SELECTION.md), tải một revision checkpoint đã chọn vào models/videberta-base bằng công cụ bạn kiểm soát, ghi lại commit và nguồn tải. Cần đủ config/tokenizer/trọng số; không chỉ có thư mục rỗng hoặc model Whisper/PhoBERT. Các script không tự tải từ Hugging Face.

## 6. Huấn luyện và đánh giá

```powershell
.venv-status-ml\Scripts\python.exe -X utf8 backend\manage.py train_candidate_status data/quality_dataset/status-bundle.json --base-model models/videberta-base --output models/status-run-001 --license-reviewed --device cuda --epochs 3
```

`--license-reviewed` chỉ được dùng khi đã kiểm tra thật. Máy không có CUDA dùng `--device cpu`, có thể chậm. Script chặn tập train thiếu bất kỳ nhãn nào trong 6 nhãn; không tự bù bằng dữ liệu giả. Max-length mặc định 256, tối đa 16 cửa sổ/cuộc; quá dài thì dừng, không cắt mất cuối cuộc. Đổi giới hạn cần cân nhắc bộ nhớ và dùng cùng cấu hình ở suy luận.

Chọn epoch bằng macro-F1 validation, chọn ngưỡng trên validation, cuối cùng đánh giá test. Báo cáo evaluation.json gồm macro-F1 không gian 6 lớp cố định, precision/recall/support, confusion matrix hàng=thật/cột=dự đoán, tỷ lệ unknown và baseline nhãn phổ biến fit chỉ từ train. Không dùng test chọn epoch/ngưỡng. Thiếu support lớp ở test thì chưa được duyệt model sử dụng.

Checkpoint safetensors + tokenizer/config được ghi vào output mới; có manifest và SHA256 các file, approved_for_use=false. Bị ngắt/lỗi có thể để lại output chưa hoàn chỉnh; không dùng thư mục đó làm model chạy web, không ghi đè để che mất thử nghiệm cũ. Không có lời khẳng định độ chính xác khi chưa chạy dữ liệu thật. Xác suất chưa được hiệu chỉnh xác suất, dù ngưỡng đã chọn trên validation.

## 7. Duyệt phát hành và mở trên web

Người phụ trách đọc report, đối chiếu lỗi nghiệp vụ (nhất là đồng ý phỏng vấn/từ chối sai), kiểm tra riêng tư/giấy phép. Lấy SHA256 thật của evaluation.json bằng Get-FileHash:

```powershell
Get-FileHash models/status-run-001/evaluation.json -Algorithm SHA256
venv\Scripts\python.exe -X utf8 backend\manage.py approve_status_model models/status-run-001 --reviewer nguoi_duyet --evaluation-sha256 SHA256_CHU_THUONG --note "Ghi nhận kiểm tra thật" --license-reviewed --confirm-evaluation
```

Cổng kỹ thuật mặc định: đủ support test cho cả 6 lớp, macro-F1 >=0.6 và cao hơn baseline. Đây là sàn kiểm tra cấu hình, không thay nghiệm thu nghiệp vụ hoặc bằng chứng tổng quát hóa. Có thể yêu cầu sàn cao hơn bằng --minimum-macro-f1. Không sửa report/manifest thủ công để qua cổng. Tài khoản reviewer phải có quyền trong database Django đang dùng.

Môi trường web cần dependency ML tương thích checkpoint đã kiểm tra, hoặc dùng một bản backend riêng có đủ dependency. Sau khi cài/kiểm tra, đặt biến trước khi chạy Django:

```powershell
$env:STATUS_MODEL_DIR='D:\NCKH\models\status-run-001'
venv\Scripts\python.exe -X utf8 backend\manage.py runserver 127.0.0.1:8002
```

Nút Phân loại ViDeBERTa chỉ mở khi manifest đúng taxonomy đã duyệt và dependency đã có. Model chỉ đọc local safetensors, kiểm checksum trước mỗi lần chạy, không trust remote code. CPU, tối đa một request model đồng thời trong mỗi process; không queue tự retry. Giới hạn cửa sổ không phải hard timeout của native inference. Đây là runtime local cần đo tải trước khi phát hành nhiều người dùng; chưa phải worker GPU production.

Dự đoán luôn là draft, không có bằng chứng tự sinh. Tạo bản thủ công, chọn nguồn và xác nhận trước khi dùng; không tạo lịch hoặc tự loại ứng viên. Không bật STATUS_MODEL_DIR khi chưa có checkpoint đạt nghiệm thu thật.
