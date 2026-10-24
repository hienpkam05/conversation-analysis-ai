# Hợp đồng API trạng thái ứng viên

Base `/api/candidate-status/`. Dùng session/CSRF và quyền annotate_quality/review_quality từ 007. Lỗi theo `{error:{code,message}}`. 401 chưa đăng nhập, 403 thiếu quyền, 404 không trong phạm vi, 409 xung đột, 422 dữ liệu không hợp lệ.

- `GET config/`: taxonomy_version, labels (code/title/description/next_step), provider=rules, model_available=false, confidence=null.
- `GET revisions/{uuid}/decisions/`: items mới nhất trước và current_confirmed (chỉ đúng snapshot/revision hiện tại; null khi không có). Bản ghi có snapshot utterances, evidence_ids, rationale, source, label, status, version, author, confirmed_by/at, stale, supersedes_id, suggested_next_step. next_step là mô tả, không có tác vụ tự chạy.
- `POST revisions/{uuid}/decisions/`: body `{source:"rules"}` tạo gợi ý; hoặc `{source:"manual",label,evidence_ids,rationale,supersedes_id?}` tạo bản thủ công độc lập. Supersedes phải cùng revision và nằm trong phạm vi. Nhãn cụ thể cần ít nhất một dẫn chứng ứng viên; unknown cần lý do. Trả 201. Không sửa bản cũ.
- `POST decisions/{uuid}/confirm/`: `{expected_version:1,confirmed_content:true}`. Tác giả hoặc reviewer; đúng phiên bản, transcript/role đã kiểm tra, revision/hash/snapshot hiện hành, không có audio no_speech/unclear. Trả 200, status=confirmed, version tăng. Lặp cùng phiên bản mới trả 200; phiên bản cũ trả 409.

Không PUT/DELETE quyết định. Muốn sửa bản đã lưu, tạo bản manual có supersedes_id. Bản xác nhận mới thay trạng thái hiện hành theo thời điểm xác nhận, không xóa lịch sử. Không có API train hoặc endpoint ViDeBERTa giả.

## Phần B: dữ liệu và mô hình

- `GET taxonomy/`: định nghĩa nhãn, hash hiện tại, audit phê duyệt (null nếu chưa duyệt đúng hash).
- `POST taxonomy/approve/`: reviewer, `{definition_hash,confirmed_definitions:true,note}`; phê duyệt định nghĩa đang hiển thị, không tự duyệt khi migrate. Audit bất biến.
- `POST decisions/{uuid}/review/`: reviewer khác tác giả, nhãn manual đã confirmed, taxonomy đúng hash đã duyệt, snapshot hiện hành. Body `{expected_version,verdict:"approved"|"rejected",note}`; audit duy nhất/bất biến, muốn sửa tạo decision mới. Bản rules/model không được duyệt thẳng thành nhãn train.
- `GET training-status/`: reviewer; thống kê nhãn, review, bất đồng nhãn đã duyệt, nguồn chưa kiểm tra và khả năng xuất. Không trả transcript trong báo cáo.
- config bổ sung `model` (available/code/message/model_version), taxonomy_approved. Không có checkpoint được duyệt thì nút AI khóa.
- source=model: chỉ checkpoint local có manifest đã duyệt đúng taxonomy hash; output không tự tạo dẫn chứng hoặc giải thích giả, status=draft. Phải copy manual/chọn bằng chứng rồi xác nhận.

Huấn luyện/đánh giá là lệnh offline, không chạy trong HTTP request. Không tự tải model, xuất dữ liệu lên dịch vụ khác hoặc duyệt checkpoint.
