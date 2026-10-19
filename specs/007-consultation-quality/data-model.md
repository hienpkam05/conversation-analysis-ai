# Mô hình dữ liệu 007

Các bảng dưới đây mô tả schema mục tiêu. Dữ liệu thủ công có migration 0001–0006; migration 0007 bổ sung AssessmentJob, QualityWorkerSlot và inference_metadata. ID dùng UUID; thời gian lưu có múi giờ.

Đã triển khai Conversation, Revision (class tương ứng ConversationRevision), Utterance, RubricVersion, Assessment, CriterionRating, Evidence. JSON snapshot vẫn giữ để tương thích và bảo toàn lịch sử; ghi bảng con trong cùng transaction. AudioSample giữ đường dẫn local chỉ phía server, metadata STT và tình trạng bản ghi. Revision có transcript_reviewed riêng với roles_confirmed. Conversation thêm members để hai người cùng chấm pilot; Assessment có author/reviewer. Nhãn cũ thiếu người chấm giữ null. Xem implementation.md.

| Thực thể | Thuộc tính chính | Ràng buộc |
| --- | --- | --- |
| Conversation | id, source_type, source_reference, created_at, owner | nguồn `text` hoặc `stt`; source_reference không chứa URL token |
| ConversationRevision | id, conversation_id, revision_number, content_hash, status, roles_confirmed, created_at | unique conversation + revision; chỉ draft được sửa, sealed bất biến |
| Utterance | id, revision_id, position, role, text, start_seconds, end_seconds, unclear | unique revision + position; role consultant/candidate/unknown; timestamp null hoặc 0 <= start < end |
| RubricVersion | id, version, status, criteria_json, created_at | version unique; draft/approved/retired; bản đã dùng không sửa |
| Assessment | id, revision_id, rubric_id, source, status, model_version, preprocessing_version, supersedes_id, total_score, created_at, reviewed_at, reviewer | source manual/model; draft/needs_review/approved; 0 <= total <= 100 hoặc null |
| CriterionRating | id, assessment_id, criterion_code, score, confidence, comment, review_required | unique assessment + code; score 0/1/2 hoặc null; null phải có lý do không đủ dữ liệu |
| Evidence | id, rating_id, kind, utterance_ids, explanation | kind quote/absence; ID phải thuộc đúng revision; quote cho điểm 1/2 có lượt của consultant |
| AssessmentJob | id, revision_id, rubric_id, model_version, status, assessment_id, error_code, created_at, finished_at | queued/running/succeeded/failed; kiểm soát số job chạy đồng thời |

`criteria_json` lưu mã, tên, mô tả, mô tả từng mức và trọng số; tổng trọng số bằng 1. Không chỉ lưu nhãn tiêu chí ngoài cấu hình model vì dễ chấm bằng rubric mới cho checkpoint cũ.

Revision đã được đánh giá phải sealed. Sửa hội thoại sao chép sang revision mới với ID lượt mới. Bản đánh giá giữ nguyên liên kết revision cũ. Model không được trả đoạn trích tự tạo: API lấy văn bản bằng các utterance ID đã xác thực.

Với absence, danh sách lượt nói là phạm vi đã xem xét và phải có giải thích; không trình bày như câu trích dẫn. Confidence là số từ 0 đến 1 hoặc null cho chấm thủ công, khác với score 0/1/2.

Nguồn STT hiện trả JSON, chưa phải thực thể transcript được lưu trong database. Chuyển từ trang audio cần tạo Conversation/Revision mới từ dữ liệu đã kiểm tra, không giả định có khóa ngoại đến một bảng STT đã tồn tại.

Quyền đã áp dụng: owner/members và tài khoản có review_quality được truy cập; annotate_quality cần cho người chấm thường. Người chấm thường chỉ đọc đánh giá do chính mình tạo để chấm độc lập. API ghi dùng session + CSRF. Chưa nghiệm thu môi trường Internet. Không log nội dung lời thoại; xuất tập train và xử lý thông tin nhận dạng thuộc D.

PilotResolution lưu revision/rubric, hai assessment từ hai tác giả khác nhau, bản kết luận riêng, người phân xử, lý do và thời điểm. Unique revision+rubric; chốt rubric cần ba conversation khác nhau đã có biên bản. Duyệt rubric không duyệt hàng loạt nhãn.

AssessmentJob lưu thêm requested_by/request_key (unique cặp), manifest_hash/revision_hash/rubric_hash, preprocessing_version, worker_token, started_at và progress cửa sổ. Job không bị xóa khi sửa hội thoại; FK PROTECT giữ bằng chứng nguồn. QualityWorkerSlot có một hàng id=1 do migration tạo, token/lease_until/last_seen cho supervisor một slot. inference_metadata giữ xác suất/thông tin cần duyệt bất biến; CriterionRating.confidence được ghi từ metadata model, không gọi là độ chính xác đã hiệu chỉnh. API không cho sửa snapshot model, chỉ tạo manual copy liên kết supersedes.
