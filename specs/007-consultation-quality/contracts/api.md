# Hợp đồng API 007

Cập nhật A/B/E: 2026-10-19. Base `/api/quality/`, JSON UTF-8, UUID cho tài nguyên quality. Đã có điều phối job/worker/provider local; chưa có checkpoint chất lượng tư vấn thật. Đọc AI_RUNTIME.md để phân biệt kiểm thử điều phối với nghiệm thu model.

## Phiên và quyền

| Phương thức | Đường dẫn tương đối | Hành vi |
| --- | --- | --- |
| GET | `session/` | Công khai, trả authenticated/username/user_id/can_review/csrf_token |
| POST | `session/` | username/password; đăng nhập bằng Django session, trả CSRF token mới |
| DELETE | `session/` | Đăng xuất, trả trạng thái phiên và CSRF token |

Mọi thao tác ghi cần cookie session/csrf và header `X-CSRFToken` từ GET session (kể cả login). Login xoay token nên client thay bằng token mới. Mọi API khác cần đăng nhập và quyền annotate_quality hoặc review_quality. CSRF sai trả 403 JSON CSRF_FAILED. Không nhận reviewer/owner/source=model do client tự gán.

Người phụ trách có review_quality xem mọi hội thoại và bản chấm. Người chấm thường chỉ xem hội thoại có owner là mình hoặc được giao qua members; chỉ xem assessment do chính mình tạo. Audio cũng kiểm tra quyền. Tài nguyên ngoài quyền trả 404, danh sách đã lọc. Danh tính do session quyết định, không nhận tên người chấm từ body.

## Hội thoại và revision

| Phương thức | Đường dẫn | Hành vi |
| --- | --- | --- |
| GET | `conversations/?offset=0&limit=100` | count/offset/limit/items; limit 1–100; không trả lời thoại |
| POST | `conversations/` | Tạo hội thoại thuộc người gửi và revision draft, 201 |
| GET | `conversations/{id}/` | Metadata và các revision mới nhất trước |
| GET | `revisions/{id}/` | Nội dung revision, trạng thái, số, hash |
| PUT | `revisions/{id}/` | Chỉ draft, cần expected_content_hash; 409 nếu stale/sealed |
| POST | `conversations/{id}/revisions/` | Tạo revision mới từ nội dung gửi; cần expected_revision_id bằng bản mới nhất |
| POST | `revisions/{id}/seal/` | Khóa nội dung; gọi lại khi đã sealed vẫn trả 200 |

Body tạo/sửa:

```json
{
  "title": "Cuộc tư vấn mẫu",
  "source_type": "text",
  "roles_confirmed": false,
  "transcript_reviewed": false,
  "utterances": [
    {"role": "consultant", "text": "Chào chị, em gọi để tư vấn công việc.", "start_seconds": null, "end_seconds": null},
    {"role": "candidate", "text": "Chị muốn tìm việc gần nhà.", "start_seconds": null, "end_seconds": null}
  ]
}
```

ID thiếu được server tạo; position tính theo thứ tự. Role consultant/candidate/unknown; timestamp cả hai null hoặc hữu hạn 0 <= start < end. unclear boolean tùy chọn. Tối đa 5.000 lượt, 10.000 ký tự/lượt và 200.000 ký tự tổng. Xác nhận vai trò không được còn unknown. source_type chỉ text/stt; không nhận URL/đường dẫn audio tùy ý.

Copy revision cần utterances, hai cờ xác nhận và expected_revision_id. Server cấp ID lượt mới và trả utterance_id_map để ánh xạ dẫn chứng chưa lưu. Revision cũ không đổi; số tăng trong cùng hội thoại. Response có id/conversation_id/title/utterances/roles_confirmed/transcript_reviewed/source_type/status/revision_number/content_hash/audio_url/review_flags.

PUT draft dùng expected_content_hash để phát hiện ghi đè. Đã seal hoặc có bất kỳ assessment nào thì không sửa được. Vue mặc định lưu chỉnh sửa thành revision mới để giữ lịch sử; API PUT phục vụ editor draft.

## Rubric và chốt nghiệp vụ

| Phương thức | Đường dẫn | Hành vi |
| --- | --- | --- |
| GET | `rubrics/` | Danh sách phiên bản mới nhất trước, đầy đủ quy tắc/mức điểm/trạng thái |
| POST | `rubrics/` | Người phụ trách tạo phiên bản nháp mới, 201 |
| PUT | `rubrics/{id}/` | Sửa draft chưa có assessment; giữ nguyên version |
| POST | `rubrics/{id}/approve/` | Chốt draft sau ít nhất 3 cuộc gọi có biên bản pilot |

Rubric gồm version (1–80 ký tự chữ/số/chấm/gạch nối/gạch dưới), general_rules (1–20 chuỗi), criteria đủ năm mã: opening/needs/job_information/interaction/next_steps. Mỗi mục có name/description/weight/levels (0,1,2)/not_assessable/boundary/example. Chuỗi bắt buộc không trống, tối đa 5.000 ký tự. weight hữu hạn >0, <=1, tổng bằng 1.

Version unique. Bản đã dùng hoặc đã duyệt không sửa định nghĩa/trọng số; phải tạo version mới và chấm lại. Snapshot đánh giá cũ giữ nguyên. POST approve nhận `confirm_business_rules: true` và `note` bắt buộc. Lưu approved_by/approved_at/approval_note; không tự duyệt các assessment.

## Đánh giá thủ công

| Phương thức | Đường dẫn | Hành vi |
| --- | --- | --- |
| GET | `revisions/{id}/assessments/` | Lịch sử được phép xem |
| POST | `revisions/{id}/assessments/` | Tạo snapshot mới, 201; khóa revision |
| GET | `assessments/{id}/` | Chi tiết snapshot, tác giả, reviewer, điểm và dẫn chứng |
| POST | `assessments/{id}/approve/` | Người phụ trách duyệt bản needs_review dùng rubric approved |

Body tạo dùng rubric_id hoặc rubric_version (nếu gửi cả hai phải khớp), status draft/needs_review, ratings đủ năm mã; supersedes_id tùy chọn phải cùng revision/rubric và tác giả. Không ghi đè assessment cũ. Không cho POST status=approved, author/reviewer/model từ client.

Rating: criterion_code, score (int 0/1/2 hoặc null, không nhận bool), not_assessable_reason/comment, evidence={kind:quote/absence,utterance_ids,explanation}. Dẫn chứng phải thuộc revision; quote điểm số cần lời consultant khi hoàn tất. Absence chỉ score=0, có phạm vi lượt nói và giải thích trong comment/explanation. Không đủ dữ liệu cần lý do; total_score=null, không tự chuẩn hóa lại phần thiếu. Đủ năm điểm/bằng chứng thì tổng = sum(score/2 * weight * 100).

Draft cho phép thiếu lý do/bằng chứng để lưu dở, nhưng không nhận ID dẫn chứng ngoại lai/điểm sai. needs_review yêu cầu transcript_reviewed và roles_confirmed, validation hoàn chỉnh; sample no_speech/unclear bị chặn. Snapshot giữ rubric lúc chấm; trạng thái phê duyệt rubric hiện tại đọc từ RubricVersion.

Approve nhận note bắt buộc, lưu reviewer/reviewed_at/review_note. Không tự duyệt bản độc lập do chính mình chấm. Bản kết luận pilot là ngoại lệ vì đã có hai tác giả độc lập, cần thao tác duyệt riêng. Không tự train hoặc tự xuất nhãn.

## Pilot chấm kép

| Phương thức | Đường dẫn | Hành vi |
| --- | --- | --- |
| GET | `pilot-resolutions/?rubric_id={id}` | Người phụ trách xem biên bản, distinct_calls, required_calls=3 |
| POST | `pilot-resolutions/` | Tạo bản kết luận và biên bản, 201 |

POST nhận assessment_ids (đúng hai UUID khác nhau), ratings (kết luận đủ validation), rationale bắt buộc. Hai bản manual needs_review phải cùng revision/rubric draft, hai tác giả khác nhau có danh tính, người phân xử khác cả hai. Audio phải là mẫu đã được xác nhận usable/incomplete, transcript và vai trò đã được kiểm tra. Mỗi revision+rubric chỉ có một biên bản. Không sửa/xóa hai bản gốc, không tự dùng trung bình điểm. Chốt rubric đếm ba conversation khác nhau, không đếm ba revision của một cuộc.

## Audio

| Phương thức | Đường dẫn | Hành vi |
| --- | --- | --- |
| GET | `samples/` | Danh mục thuộc quyền xem, trạng thái STT và chấm; không lộ source_path |
| GET | `samples/{id}/audio/` | Phát audio local; Range 206/416; không nhận đường dẫn client |
| POST | `samples/{id}/review/` | disposition/note; kiểm tra tình trạng, không duyệt nhãn |

disposition: unreviewed/usable/no_speech/unclear/incomplete. Ba trạng thái cuối cần ghi chú. Response review luôn approved_for_training=false vì đây không phải endpoint duyệt assessment.

## Job AI và bản sửa thủ công

| Phương thức | Đường dẫn | Hành vi |
| --- | --- | --- |
| GET | `model-status/` | Chỉ đọc metadata, không tải trọng số; available/code/message/model_version/rubric_version/preprocessing_version/requires_human_review; worker_last_seen/max_concurrency/timeout_seconds |
| GET | `revisions/{id}/assessment-jobs/` | Tối đa 20 job mới nhất thuộc quyền xem |
| POST | `revisions/{id}/assessment-jobs/` | rubric_id và request_key UUID; 202 queued hoặc job trùng đã có |
| GET | `assessment-jobs/{id}/` | Trạng thái, progress, assessment_id hoặc lỗi cố định |
| POST | `assessments/{id}/manual-copy/` | Tạo manual draft riêng từ bản model thuộc quyền xem; 201 |

POST job cần revision sealed, transcript_reviewed/roles_confirmed và có nội dung, rubric approved khớp manifest. Thiếu model/dependency/manifest trả 503 và không tạo job. Rubric khác checkpoint trả 409; chưa duyệt trả 422; queue đầy trả 429. Client không chọn path/model/version tùy ý. request_key cùng người/tài nguyên tái sử dụng job; nếu dùng cho revision/rubric khác trả 409. Job đang queued/running cùng người/revision/rubric/manifest được tái sử dụng. Không tự retry job failed.

Job response: id/revision_id/rubric_id/status/model_version/preprocessing_version/completed_windows/total_windows/assessment_id/created_at/started_at/finished_at/error. error null trừ trạng thái failed, khi đó có code/message đã chuẩn hóa. Không trả path/token worker/text/trace. queued/running chưa có assessment_id; succeeded trỏ đúng snapshot nguồn model; failed không có điểm thành công giả.

Quyền xem job: người gửi hoặc review_quality, đồng thời có quyền truy cập hội thoại. Người chấm thường được xem assessment model do mình yêu cầu, không nhìn thấy job/điểm của người khác được giao chung hội thoại. Kết quả model không có tác giả thủ công; metadata chứa probabilities/confidence/windows/evidence_verified=false/review_required=true/confidence_calibrated=false. Model version/preprocessing version luôn lưu.

Provider chưa có cơ chế chọn bằng chứng được duyệt, vì vậy ratings có evidence rỗng, total_score=null, status=needs_review. Điểm dưới ngưỡng cấu hình thành null kèm lý do; xác suất không được gọi là độ chính xác. Output có NaN/thiếu lớp/mã sai/trường evidence tự tạo bị từ chối trước khi ghi database.

manual-copy chỉ nhận bản source=model; ratings được sao chép sang manual draft, tác giả session, supersedes trỏ AI gốc. Không sao chép xác suất/model metadata. Chỉnh và lưu tạo snapshot tiếp theo, supersedes trỏ bản thủ công trước. API approve không nhận bản source=model dù điểm cao hoặc có ai gửi thêm evidence từ client. Người dùng cần đối chiếu/chọn dẫn chứng, hoàn tất manual và duyệt theo A/B. AI gốc không đổi.

Worker một slot, timeout/lease/process con riêng; xem AI_RUNTIME.md. Web dừng polling khi terminal/đổi hội thoại/rời tab/unmount/logout hoặc lỗi mạng; việc dừng polling không hủy job đang chạy.

## Lỗi JSON

```json
{"error":{"code":"REVISION_SEALED","message":"Bản đã khóa; tạo revision mới để sửa."}}
```

401 UNAUTHORIZED; 403 FORBIDDEN/CSRF_FAILED; 404 NOT_FOUND; 405 METHOD_NOT_ALLOWED; 409 REVISION_CONFLICT/REVISION_SEALED/RUBRIC_LOCKED/WRITE_CONFLICT/RUBRIC_MODEL_MISMATCH/MODEL_CHANGED; 413 INPUT_TOO_LARGE; 422 INVALID_INPUT/INVALID_EVIDENCE/ROLES_UNCONFIRMED/AUDIO_NOT_ASSESSABLE/RUBRIC_NOT_APPROVED; 429 QUEUE_FULL; 503 DATABASE_UNAVAILABLE/QUALITY_MODEL_UNAVAILABLE/MODEL_MANIFEST_INVALID/MODEL_NOT_APPROVED/MODEL_DEPENDENCIES_MISSING. Job failed có thể mang MODEL_LOAD_FAILED/MODEL_INFERENCE_FAILED/MODEL_OUTPUT_INVALID/JOB_TIMEOUT/WORKER_INTERRUPTED/ACCESS_REVOKED/REVISION_CHANGED. JSON hỏng trả 422. Không trả trace hoặc nội dung hội thoại trong lỗi hệ thống có kiểm soát.
