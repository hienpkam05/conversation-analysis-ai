# Tình trạng triển khai 007

Cập nhật: 2026-10-19. Phân biệt chức năng đã làm với nghiệp vụ đã được con người xác nhận.

## Phần A: Công cụ sẵn sàng, chờ duyệt thật

- quality-draft-v2 định nghĩa năm tiêu chí, mức 0/1/2, không đủ dữ liệu, dẫn chứng, ví dụ giả định và trọng số. Hướng dẫn tại ANNOTATION_GUIDE.md.
- Quản lý rubric trên web: sửa bản nháp chưa sử dụng, tạo phiên bản mới nếu đã dùng. Trọng số tổng bằng 1; tổng điểm tính theo trọng số trên server, có mục không đủ dữ liệu thì tổng null.
- Hai người chấm độc lập cùng revision và rubric; người chấm thường không xem được bản chấm của nhau. Người phụ trách có màn đối chiếu từng tiêu chí, ghi lý do và tạo bản kết luận riêng, không ghi đè hai bản gốc.
- Người phân xử phải khác hai người chấm. Pilot phải gắn audio đã xác nhận usable/incomplete, transcript và vai trò đã kiểm tra.
- Cần ít nhất ba cuộc gọi khác nhau có biên bản trước khi chốt rubric. Ba revision của một cuộc không thay thế ba cuộc gọi. Lưu tài khoản, thời điểm và kết luận nghiệp vụ khi duyệt.
- Nhãn được duyệt riêng sau khi rubric được chốt. Không tự duyệt bản chấm độc lập của mình; bản kết luận pilot có hai nguồn độc lập được người phân xử duyệt riêng. Không tự chạy train.

T001/T003/P007/P011 còn mở vì chưa có người nghe, gán nhãn và chốt nghiệp vụ trên audio thật. Không dùng fixture kiểm thử làm bằng chứng nghiệp vụ.

## Phần B: Đã triển khai

- Django giữ SQLite backend/db.sqlite3 theo cấu hình hiện tại, không dùng PostgreSQL matching. check_quality_storage kiểm tra đọc/ghi/rollback, dữ liệu chuẩn hóa và dung lượng.
- Conversation có owner/members, nguồn và tham chiếu nội bộ không chứa đường dẫn/token. Người phụ trách xem toàn bộ; người chấm chỉ xem hội thoại mình sở hữu/được giao. Danh sách, chi tiết, audio và đánh giá đều kiểm tra quyền. Hội thoại cũ chưa có owner không tự mở cho mọi tài khoản.
- Migration 0005/0006 bổ sung revision_number/content_hash/status, Utterance, RubricVersion, CriterionRating, Evidence, nguồn/owner, tác giả/người duyệt/supersedes, PilotResolution. Backfill giữ JSON và nhãn cũ, không bịa người chấm hoặc phê duyệt.
- JSON giữ làm snapshot tương thích API cũ. Bảng con được ghi trong transaction khi tạo/sửa qua service/API; không chỉnh bảng con bằng SQL hoặc QuerySet.update. Đối chiếu bằng lệnh kiểm tra storage.
- PUT chỉ sửa draft với expected_content_hash. POST seal khóa revision. Mọi assessment, kể cả nháp, khóa transcript liên quan. Sửa sau đó tạo revision mới với số tăng và ID lượt mới; frontend ánh xạ lại dẫn chứng chưa lưu. Assessment là snapshot, bản thay thế dùng supersedes_id.
- Session Django, quyền annotate_quality/review_quality, CSRF cho thao tác ghi. quality_user nhập mật khẩu ẩn, không có mật khẩu mặc định. GET session cấp CSRF; login xoay token; logout thu hồi phiên.
- API JSON cho lỗi dữ liệu/quyền/not found/xung đột/database bận. Danh sách hội thoại có offset/limit. Hợp đồng tại contracts/api.md.

## Audio và giao diện

Giữ 20 mẫu: 19 transcript nháp, 1 no_speech, 325 đoạn. Tất cả cần nghe/sửa/gán vai. Heuristic gắn cờ STT đáng nghi không tự xóa câu. Export transcript có purpose=human_review_only, không xuất nhãn train/đường dẫn audio.

Vue có đăng nhập, chọn audio và rubric, nghe/tua audio, editor lượt nói, xác nhận, chấm dẫn chứng, nháp/chờ duyệt và lịch sử theo revision. Người phụ trách có quản lý rubric, biên bản pilot, duyệt rubric/nhãn. Lưu không tự biến dữ liệu nháp thành nhãn được duyệt.

## Giới hạn

Chưa có tập nhãn thật được duyệt trong database hiện tại, fine-tune, checkpoint inference hoặc F1 thật. D và nghiệm thu chất lượng E chưa hoàn thành. model-status báo không có model; khi chưa cấu hình checkpoint, POST job trả 503, không sinh điểm giả.

## Tích hợp E

Đã có migration 0007 cho AssessmentJob/QualityWorkerSlot/inference_metadata, API submit/list/detail/manual-copy, provider local theo manifest và worker supervisor một slot có process con/timeout/lease. Vue hiển thị nguồn AI/progress/lỗi, dừng polling khi rời tab/đổi revision/xong; bản sửa thủ công tách riêng. Xem AI_RUNTIME.md và biên bản E.

Provider thực hiện load strict safetensors cho encoder + 5 đầu, token-window bao phủ phần cuối và trung bình xác suất. Đây là hợp đồng code cần pipeline D xuất đúng định dạng; chưa chạy được trên model thật. Không có extractor dẫn chứng đã duyệt nên mọi kết quả model luôn needs_review, evidence rỗng và total null; API không cho approve trực tiếp AI. Bản thủ công cần chọn dẫn chứng/hoàn tất/duyệt theo A/B.

Unit test mock provider trong database test riêng để kiểm tra các nhánh điều phối. Trình duyệt kiểm tra cả worker spawn thật nhánh thiếu model và dữ liệu fixture riêng để kiểm tra hiển thị/sửa, sau đó xóa fixture. Không coi đây là huấn luyện hoặc báo cáo chất lượng. AC-08/T026 còn mở.

## Chuẩn bị D

Đã có exporter nhãn approved với schema/hash/che định danh và yêu cầu người rà riêng tư; chia nhóm không tách cùng ứng viên/nội dung trùng sang các tập; baseline majority train-only và báo cáo macro-F1/confusion/MAE/mask NA. Kiểm thử bằng database test riêng; không dùng fixture để train model thật. Xem TRAINING.md và MODEL_SELECTION.md.

Kiểm tra database ngày 2026-10-19: 0 assessment, rubric draft. Lệnh export train đã từ chối đúng; chưa có file tập train/split/report thật được tạo. Chờ người dùng cung cấp vị trí nhãn nếu đã chấm ở nguồn khác. Không tự cài torch/transformers hoặc tải checkpoint khi chưa có dữ liệu hợp lệ.

Bản này chạy phát triển trên localhost; không coi là đã nghiệm thu Internet. Trước khi dùng chung cần secret, DEBUG=false, HTTPS/cookie secure, database phù hợp, sao lưu và giới hạn đăng nhập/upload ở tầng triển khai. Chưa thử tải PostgreSQL cho quality.

Xem quickstart.md và quickstart-run-2026-10-19-ab.md để chạy và kiểm tra.
