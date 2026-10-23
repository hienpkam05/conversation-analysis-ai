# Dữ liệu 008

| Bảng | Nội dung |
| --- | --- |
| Summary | UUID, revision FK PROTECT, revision_hash, utterances snapshot, sections, source extractive_rules/manual, metadata method/omitted_matches, draft/approved, author, supersedes, version, reviewed_by/at |
| Appointment | UUID, summary FK PROTECT, owner, request_key unique theo owner, title/participant/responsible/channel/location, starts_at/ends_at aware hoặc cùng null, evidence_ids, draft/confirmed/cancelled, version, confirmed_by/at |
| AppointmentEvent | UUID, appointment, actor, action created/updated/confirmed/cancelled, snapshot, thời điểm |

sections là năm nhóm context/needs/job/questions/next_steps, mỗi nhóm tối đa 20 ý. Một ý gồm text và danh sách utterance_ids thuộc snapshot. Tổng tối đa 100.000 ký tự. Bản tự động dùng nguyên văn, bản thủ công có thể diễn đạt lại và phải có dẫn chứng; không giả văn bản diễn đạt lại là câu trích nguồn.

Thông tin lịch do người dùng nhập, không tạo FK giả đến ứng viên/recruiter ở database khác. Các giá trị participant/responsible có thể chứa thông tin cá nhân, chỉ hiển thị theo quyền, không log toàn bộ hoặc đưa fixture/audio lên Git. Kiểm tra trùng giờ giới hạn lịch do cùng owner tạo; không bảo đảm người tham gia không có lịch bên ngoài hệ thống.

Thời gian lưu aware/UTC theo Django, hiển thị Asia/Ho_Chi_Minh. Không lấy thời điểm upload làm ngày diễn ra cuộc gọi để diễn giải “ngày mai”.
