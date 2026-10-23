# API 008

Base /api/followup/. Dùng session /api/quality/session/ và CSRF header hiện có. Mọi endpoint cần quyền annotate_quality hoặc review_quality và quyền truy cập hội thoại. Không có endpoint công khai chứa transcript/lịch.

| Method | Path | Kết quả |
| --- | --- | --- |
| GET/POST | revisions/{id}/summaries/ | Danh sách 50 bản mới nhất / tạo bản trích dẫn draft 201 |
| GET/PUT | summaries/{id}/ | Chi tiết / sửa manual draft với expected_version + sections |
| POST | summaries/{id}/copy/ | Tạo manual draft riêng, supersedes trỏ bản gốc |
| POST | summaries/{id}/approve/ | confirmed_content=true + expected_version; cần transcript reviewed, roles confirmed, snapshot mới nhất; 200 |
| GET/POST | appointments/ | Tối đa 100 lịch được phép đọc, lọc summary_id / tạo draft với request_key UUID |
| PUT | appointments/{id}/ | Sửa draft, expected_version; 409 nếu stale/không còn draft |
| POST | appointments/{id}/confirm/ | expected_version + confirmed_with_participants=true, kiểm tra đủ điều kiện và trùng lịch |
| POST | appointments/{id}/cancel/ | Hủy idempotent, lưu event; 200 |

Summary response: revision_id/conversation_id/sections/utterances snapshot/source/status/version/author/reviewed_by/at/stale/metadata/categories. Snapshot nguồn không đổi, stale khi revision/hash thay đổi. Mọi ý thủ công cần utterance_ids không rỗng và thuộc snapshot.

Appointment body: summary_id (khi tạo), request_key (khi tạo), title, participant, responsible, channel (phone/online/onsite), location, starts_at/ends_at (ISO có offset hoặc cả hai null để draft), evidence_ids. Confirm yêu cầu ngày giờ tương lai, duration <=8h, người tham gia/phụ trách/location không trống, summary approved còn current, bằng chứng có cả candidate/consultant và cờ xác nhận true. Không có tự parse ngày trong text.

Appointment response gồm status/version/confirmed_by/at và events actor/action/time. Body owner/status/confirmed_by do client tự gửi không quyết định quyền hoặc trạng thái. Lịch draft không đồng nghĩa lịch đã xác nhận hay đã gửi lời mời. Mọi tác vụ đều local database, không gửi email/SMS/calendar.

401 chưa đăng nhập; 403 thiếu quyền/CSRF; 404 ngoài phạm vi; 409 version conflict/stale/đã duyệt hoặc trùng thời gian; 422 input/evidence/time/consent không hợp lệ; 503 database bận theo wrapper Django hiện có. Không trả trace/nội dung nguồn trong lỗi.
