# Chuẩn bị huấn luyện chất lượng tư vấn

Cập nhật 2026-10-19. Các lệnh dưới đây đã có code và kiểm thử bằng database test riêng. Database thật hiện chưa có assessment, rubric quality-draft-v2 vẫn draft; chưa xuất/chia tập thật, chưa chạy baseline thật hoặc fine-tune. Transcript không phải nhãn.

## 1. Kiểm tra nhãn

Chạy tại thư mục gốc dự án:

```powershell
venv\Scripts\python.exe -X utf8 backend\manage.py quality_training_status
```

Chỉ dùng assessment nguồn manual, trạng thái approved, có author/reviewer/reviewed_at, thuộc rubric đã được người phụ trách duyệt đầy đủ. Revision mới nhất phải sealed, transcript và vai trò đã được xác nhận, không còn unknown. Audio phải được xác nhận usable/incomplete. Bản nháp/chờ duyệt, nhãn mâu thuẫn chưa phân xử, nhãn hết hiệu lực do có bản thay thế đã duyệt và bản ghi không đủ điều kiện không được dùng.

Một cuộc gọi chỉ có một kết luận. Nếu đã có biên bản pilot được duyệt, lấy kết luận đó; nếu có nhiều nhãn approved khác điểm nhưng không có kết luận phù hợp thì loại khỏi export. Nhãn cùng điểm lấy bản mới nhất; không nhân bản thành nhiều mẫu. Revision mới chưa được duyệt không khiến exporter quay lại bản cũ để tận dụng nhãn. Phiên bản rubric không được trộn lẫn.

Nếu nhãn nằm ngoài Django, gửi đường dẫn file và mô tả mã cuộc gọi, phiên bản transcript, năm điểm, người chấm/người duyệt. Chưa có importer tự coi CSV/Excel bất kỳ là nhãn được duyệt; phải kiểm tra và đối chiếu trước.

## 2. Chuẩn bị nhóm và thông tin cần che

Hai file riêng tư, đặt dưới data/quality_dataset/ để Git ignore:

- groups.json: object khóa là Conversation UUID gốc, giá trị là mã nhóm ứng viên/chuỗi liên hệ đã được người phụ trách đối chiếu. Tất cả cuộc gọi cùng người hoặc cùng chuỗi phải chung nhóm. Không giả định mỗi tên file là một ứng viên độc lập. Lấy UUID từ API hội thoại mà tài khoản có quyền truy cập.
- redact-terms.json: array tên người, địa chỉ, tên tài khoản, định danh riêng cần che trong nội dung. Chỉ điền thông tin thực sự cần che; không thay từ khóa nghiệp vụ để làm mất căn cứ chấm.

Ví dụ cấu trúc (thay UUID bằng hội thoại thực tế, không phải nhãn mẫu để train):

```json
{
  "11111111-1111-4111-8111-111111111111": "ung-vien-001",
  "22222222-2222-4222-8222-222222222222": "ung-vien-001",
  "33333333-3333-4333-8333-333333333333": "ung-vien-002"
}
```

```json
["Tên người cần che", "Địa chỉ cá nhân cần che"]
```

Đây là manifest do người phụ trách cung cấp, không phải kết quả mô hình xác minh danh tính. Không tải nhóm/danh tính lên dịch vụ ngoài. Nhãn đã duyệt vẫn cần bảo đảm quyền sử dụng dữ liệu cho nghiên cứu.

## 3. Xuất bản để kiểm tra riêng tư

```powershell
venv\Scripts\python.exe -X utf8 backend\manage.py export_quality_training data/quality_dataset/training/approved-v1.json --rubric-version quality-draft-v2 --group-map data/quality_dataset/groups.json --redact-terms data/quality_dataset/redact-terms.json
```

Mã phiên bản rubric có thể vẫn chứa chữ draft trong tên, nhưng trạng thái trong database bắt buộc approved. Lệnh từ chối ghi đè file cũ, từ chối rubric chưa duyệt hoặc không có mẫu đủ điều kiện. Không sửa database, transcript gốc hoặc audio.

Bản xuất có schema/preprocessing/rubric version và checksum. ID nguồn/nhóm được băm; ID lượt đổi thành u0001… và dẫn chứng ánh xạ theo. Không xuất đường dẫn nguồn, tên file, tên hội thoại, tài khoản người chấm/duyệt, nhận xét tự do, lý do NA hoặc metadata STT. Nhãn null được giữ để mask loss.

Tự động che điện thoại phổ biến, email, URL, chuỗi định danh 12 số và các cụm đã khai báo. **Regex không bảo đảm ẩn danh hoàn chỉnh.** Người có trách nhiệm phải đọc toàn bộ bản xuất để tìm tên/địa chỉ/định danh còn sót và xác nhận group map. Nếu cần sửa, bổ sung danh sách che rồi xuất thành file mới; không chỉnh trực tiếp artifact đã đóng checksum.

SHA256 được in sau khi xuất. Mã này kiểm tra tính nhất quán và phiên bản, không phải chữ ký số chứng minh người duyệt hoặc quyền sử dụng.

## 4. Chia tập theo nhóm

Sau khi kiểm tra riêng tư và nhóm, thay SHA256 bằng mã vừa in:

```powershell
venv\Scripts\python.exe -X utf8 backend\manage.py prepare_quality_splits data/quality_dataset/training/approved-v1.json data/quality_dataset/training/splits-v1.json --privacy-reviewed-sha256 SHA256_CUA_BAN_DA_DOC --privacy-reviewer ma_nguoi_kiem_tra --seed 42
```

Chia trước mọi thao tác chia cửa sổ/tokenization. Gộp liên thông theo nhóm ứng viên và transcript trùng sau chuẩn hóa/che thông tin; không tách các bản trùng hoặc cùng nhóm sang tập khác. So trùng bỏ khác biệt hoa/thường, dấu câu, gán vai và chia lượt. Đây không phải bộ phát hiện trùng ngữ nghĩa; bản gần trùng cần đối chiếu thêm bằng người.

Cần tối thiểu ba nhóm độc lập để tạo ba tập không rỗng. Tỷ lệ yêu cầu 70/15/15 tính theo nhóm, không bảo đảm đúng số cuộc gọi khi nhóm có nhiều cuộc; báo cáo ghi số mẫu thực tế. Seed cố định và thứ tự dữ liệu ổn định giúp tái lập. Báo cáo phân bố 0/1/2/null theo tiêu chí/tập và cảnh báo thiếu lớp. Không giải quyết thiếu dữ liệu bằng việc nhân bản cùng cuộc gọi qua các tập.

Bundle luôn release_approved=false. Đủ ba nhóm chỉ là điều kiện kỹ thuật chia tập, không có nghĩa đủ dữ liệu để kết luận model tốt.

## 5. Baseline và báo cáo

```powershell
venv\Scripts\python.exe -X utf8 backend\manage.py train_quality_baseline data/quality_dataset/training/splits-v1.json data/quality_dataset/training/baseline-v1.json
```

Baseline đầu tiên là nhãn phổ biến theo từng tiêu chí, fit **chỉ trên train**, không dùng nhãn validation/test để chọn dự đoán. Mục đích là tạo mốc tối thiểu để so với ViDeBERTa sau này, không phải model đọc hiểu văn bản.

Báo cáo riêng validation/test: macro-F1 theo không gian cố định ba lớp 0/1/2 (lớp không có support có F1=0), confusion matrix hàng=nhãn thật/cột=dự đoán, support, số nhãn bị mask, MAE điểm tiêu chí và MAE tổng chỉ trên cuộc đủ năm điểm. Nhãn null không biến thành 0 và không được tính như mẫu đúng. Mọi dự đoán baseline cần duyệt, review_required_rate=1; chưa có bằng chứng tự động hoặc xác suất được hiệu chỉnh. Không tạo checkpoint ViDeBERTa từ baseline này.

Không chạy baseline nếu bất kỳ đầu nào không có nhãn quan sát được trong train. Không sửa seed/chia lại liên tục để chọn báo cáo test đẹp hơn. Test dùng để báo cáo cuối; chọn cấu hình/ngưỡng về sau chỉ từ validation.

## 6. ViDeBERTa và cổng phát hành còn chờ

Đề xuất thử Fsoft-AIC/videberta-base dùng encoder chung + năm đầu ba lớp. Xem MODEL_SELECTION.md: mới khảo sát nguồn chính thức, chưa đóng băng checkpoint đầy đủ hoặc nghiệm thu tokenizer/giấy phép trọng số. Không dùng model nền như model chấm chất lượng đã train.

Môi trường Python hiện tại thiếu torch/transformers/sentencepiece/safetensors; chưa tự cài các gói lớn hay tải checkpoint. Khi có dữ liệu hợp lệ sẽ chốt môi trường riêng/Colab GPU, pin revision và dependency, chia token-window giữ phần cuối, mask loss theo nhãn quan sát, tổng hợp ở cấp hội thoại và so với baseline trên đúng bundle.

T017–T020 chưa hoàn thành: chưa fine-tune, chưa có chỉ số thực nghiệm thật hoặc ngưỡng phát hành được người phụ trách duyệt. Không đặt ngưỡng tùy ý chỉ để đánh dấu xong. Chưa tích hợp kết quả baseline vào màn chấm AI của phần E.
