# Dữ liệu 009

## StatusDecision

- id: UUID.
- revision: khóa ngoại PROTECT đến phiên bản hội thoại.
- revision_hash, utterances: snapshot nguồn, không thay đổi theo các revision sau.
- taxonomy_version: candidate-status-draft-v1.
- taxonomy_hash: hash định nghĩa lúc tạo. Bản legacy thiếu hash phải tạo bản mới, không tự gán lại hash để hợp thức hóa nhãn.
- source: rules hoặc manual; chưa có source model.
- label: một trong 5 nhãn nghiệp vụ hoặc unknown.
- evidence_ids: danh sách ID lượt ứng viên nghe rõ thuộc snapshot, tối đa 200 lượt.
- rationale: nhận định/lý do, tối đa 5000 ký tự; unknown bắt buộc có lý do.
- metadata: phương pháp quy tắc, các tín hiệu khớp/mơ hồ; confidence=null.
- author, created_at: người tạo và thời gian.
- supersedes: bản trước cùng revision, nullable; bản trước không bị ghi đè.
- status: draft hoặc confirmed; version: phiên bản phục vụ xác nhận có kiểm tra xung đột.
- confirmed_by, confirmed_at: audit xác nhận, bắt buộc có khi status=confirmed.

Không cho sửa các trường nội dung qua model.save; bản confirmed không được đổi audit/trạng thái. ORM bulk update và truy cập database quản trị nằm ngoài bảo vệ ứng dụng, không dùng để duyệt hộ người dùng.

## Trạng thái hiện hành

Là bản confirmed gần nhất theo confirmed_at của revision mới nhất, hash và snapshot vẫn khớp nguồn. Bản draft mới không thay bản confirmed. Tạo revision mới làm kết quả cũ thành lịch sử, không tự mang trạng thái sang nguồn mới. Không cập nhật ứng viên/chiến dịch matching hoặc Appointment.

## Xác nhận

Tác giả hoặc reviewer xác nhận rõ nội dung + đúng expected_version; khóa hàng quyết định, conversation và revision trong transaction. Revision đã kiểm tra transcript/vai, không còn role unknown, không có audio no_speech/unclear. Sau khi xác nhận, revision được sealed; muốn sửa transcript phải tạo revision mới.

## Phần B

TaxonomyApproval lưu version duy nhất, definition_hash, definitions, reviewer/note/time; audit bất biến. Thay định nghĩa sau khi duyệt cần tăng version, không ghi đè.

LabelReview liên kết một-một decision, reviewer/verdict/note/time. Chỉ manual confirmed đúng taxonomy/nguồn hiện hành, reviewer khác tác giả. Duyệt/reject đều bất biến; sửa bằng decision mới. Đây là kiểm tra bổ sung riêng cho train, không thay status confirmed nghiệp vụ.

Source model được thêm cho dự đoán draft, không được confirm trực tiếp hoặc review thành nhãn train; cần bản manual có dẫn chứng. Cấu hình runtime qua STATUS_MODEL_DIR, dữ liệu model local và manifest không lưu chung với nhãn trong database.
