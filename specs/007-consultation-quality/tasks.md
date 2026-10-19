# Công việc 007

Tiến độ và kiểm thử ghi trong implementation.md và quickstart-run-2026-10-19-ab.md. Phần B đã triển khai cho Django local có đăng nhập. Phần A đã có công cụ duyệt nhưng chưa được người phụ trách chốt nghiệp vụ; không đánh dấu duyệt thay người dùng.

## A. Chốt nghiệp vụ

- [ ] T001 Người phụ trách duyệt thật 5 tiêu chí, định nghĩa mức 0/1/2 và trọng số; công cụ quản lý phiên bản/duyệt đã có.
- [x] T002 Định nghĩa trường hợp không đủ dữ liệu, absence và hướng dẫn chọn bằng chứng trong ANNOTATION_GUIDE.md; mới là bản nháp, chưa duyệt nghiệp vụ.
- [ ] T003 Người chấm hoàn thành pilot thật, giải quyết bất đồng và chốt rubric đầu tiên; đã có 20 mẫu và API/UI chấm kép, đối chiếu, biên bản, chặn duyệt khi chưa đủ 3 cuộc gọi.

## B. Dữ liệu và API Django

- [x] T004 Kiểm tra SQLite Django, đọc/ghi/rollback và dung lượng; sao lưu trước migration. Không đổi PostgreSQL matching.
- [x] T005 Tạo migration dữ liệu chuẩn hóa, owner/members, RubricVersion, CriterionRating, Evidence, PilotResolution; giữ snapshot cũ. AssessmentJob thuộc E/T022.
- [x] T006 PUT draft với content_hash chống ghi đè, seal và sao chép revision; đổi ID lượt khi sao chép, khóa bản đã dùng chấm.
- [x] T007 Tạo validation điểm, dẫn chứng, role, absence và tổng điểm; test các biên.
- [x] T008 API hội thoại phân trang, rubric nháp/phiên bản mới/duyệt, đánh giá thủ công/lịch sử/duyệt; session, phân quyền và CSRF. Job AI vẫn thuộc E.
- [x] T009 Kiểm thử migration nhiều revision, quyền đọc/ghi/audio, chấm độc lập, revision bất biến, chốt pilot/rubric và JSON lỗi; xem biên bản A/B.

## C. Giao diện dùng được trước model

- [x] T010 Thêm tab Đánh giá tư vấn trong Vue; nhập văn bản và nhận transcript từ trang audio.
- [x] T011 Tạo editor lượt nói: tách/gộp/sửa nội dung, gán vai trò, xác nhận vai trò.
- [x] T012 Tạo màn chấm 5 tiêu chí, chọn dẫn chứng, không đủ dữ liệu, xem tổng hợp.
- [x] T013 Lưu/mở lại hội thoại và đánh giá; phân biệt nguồn thủ công/AI, nháp/chờ duyệt/đã duyệt. Kiểm thử nguồn AI bằng fixture tách riêng; chưa có kết quả model thật.
- [x] T014 Kiểm tra luồng thủ công, lỗi API, transcript dài, desktop/mobile và production build trong bản local.

### Đợt audio mẫu

- [x] P001 Đăng ký 20 mẫu từ manifest local, chạy lại không tạo trùng.
- [x] P002 Phát audio gốc theo sample ID, hỗ trợ tua bằng HTTP Range.
- [x] P003 Lưu bản sửa trong cùng hội thoại, giữ revision cũ và kiểm tra xung đột.
- [x] P004 Lưu chấm nháp; gửi chờ duyệt chỉ sau khi xác nhận transcript/người nói và bằng chứng.
- [x] P005 Kiểm thử trình duyệt lưu/mở lại, nghe audio, revision, giữ điểm khi tách lượt và mobile; 18 tests Django qua.
- [x] P006 Hoàn tất nhận dạng toàn bộ 20 mẫu: 19 transcript nháp, 1 mẫu chưa phát hiện lời nói, 325 đoạn; xem biên bản chạy.
- [ ] P007 Người chấm nghe/sửa transcript, xác nhận vai trò và gán nhãn; rubric vẫn chưa được duyệt.
- [x] P008 Đánh dấu đoạn STT đáng nghi để nghe lại; giữ nguyên bản thô.
- [x] P009 Có lệnh xuất transcript để đối chiếu, không xuất nhãn train hoặc phê duyệt tự động.
- [x] P010 Viết hướng dẫn chi tiết năm tiêu chí và đưa mức điểm/ví dụ vào web theo quality-draft-v2; giữ nguyên các snapshot v1.
- [ ] P011 Chấm thử ba mẫu theo PILOT_REVIEW.md, giải quyết bất đồng và trình người phụ trách duyệt rubric.
- [x] P012 Có màn quản lý rubric, đối chiếu hai bản chấm, biên bản và duyệt nhãn; lưu người/thời điểm/kết luận. Không tự tạo nhãn thật.

## D. Dữ liệu huấn luyện và model

- [x] T015 Triển khai exporter chỉ lấy nhãn thủ công đã duyệt/rubric approved, che định danh, schema/hash và cổng người kiểm tra riêng tư; đã test bằng fixture, chưa có nhãn thật để xuất.
- [x] T016 Triển khai chia train/validation/test theo nhóm ứng viên và nội dung trùng trước khi tạo cửa sổ, kiểm tra rò rỉ và cảnh báo thiếu lớp; chưa tạo bộ chia dữ liệu thật.
- [ ] T017 Chốt checkpoint ViDeBERTa, giấy phép, tokenization và tài nguyên thực nghiệm.
- [ ] T018 Làm baseline, fine-tune 5 đầu; mask nhãn thiếu và xử lý hội thoại dài.
- [ ] T019 Báo cáo macro-F1 từng tiêu chí, confusion matrix, độ lệch điểm, tỷ lệ cần duyệt.
- [ ] T020 Chốt ngưỡng phát hành, ngưỡng độ tin cậy và cơ chế bằng chứng sau khi xem báo cáo.

### Chuẩn bị D ngày 2026-10-19

- [x] D001 Lệnh quality_training_status kiểm tra database; kết quả thật: 0 Assessment, quality-draft-v2 vẫn draft.
- [x] D002 Baseline nhãn phổ biến fit train-only và bộ tính macro-F1/confusion matrix/MAE/mask NA; kiểm thử fixture riêng, không phải báo cáo chất lượng thật.
- [x] D003 Viết TRAINING.md và khảo sát nguồn checkpoint trong MODEL_SELECTION.md; không tải model hoặc sửa môi trường Python hiện tại.
- [ ] D004 Nhận đường dẫn nhãn nếu nằm ngoài Django, đối chiếu/duyệt; sau đó xuất, rà riêng tư và chạy trên dữ liệu thật.

T015/T016 đánh dấu hoàn thành phần code, không khẳng định đã có tập train thật. T018/T019 còn mở cho fine-tune và báo cáo thực nghiệm; chưa có F1 hay model mới.

## E. Tích hợp AI và nghiệm thu

- [x] T021 Có provider local theo manifest, model-status không load trọng số và lỗi rõ khi thiếu model. Chưa smoke test tokenizer/checkpoint thật; chỉ xong phần code hợp đồng runtime.
- [x] T022 AssessmentJob + migration 0007, worker process con spawn, một slot/queue limit/timeout/lease và trạng thái lỗi; không retry tự động.
- [x] T023 Vue theo dõi tiến độ/lỗi/kết quả, hủy request khi rời tab/đổi revision, dừng ở trạng thái cuối; kiểm tra desktop/mobile bằng fixture riêng.
- [x] T024 Giữ AI snapshot; manual-copy và các bản chỉnh thủ công liên kết supersedes, xác nhận dẫn chứng trước duyệt; API chặn approve trực tiếp model.
- [x] T025 Test điều phối với provider mock trong database test: model thiếu/load lỗi, mismatch, giới hạn nội dung, output NaN/evidence tự tạo, quyền/lease/timeout; process worker thật đã kiểm tra nhánh thiếu checkpoint.
- [ ] T026 Nghiệm thu AC-01 đến AC-08, ghi lệnh và kết quả thật vào biên bản chạy.

Chi tiết E: AI_RUNTIME.md và quickstart-run-2026-10-19-e.md. T021–T025 hoàn thành phần tích hợp được kiểm thử, không có nghĩa đã có model trained hoặc đạt AC-08. Chưa có checkpoint/nhãn/ngưỡng được duyệt nên T026 và nghiệm thu chất lượng AI vẫn mở.

Thứ tự: A → B → C để có bản dùng được; D có thể tiến hành sau khi rubric đã duyệt và có nhãn. E phụ thuộc cả C và D. Không đánh dấu D/E xong bằng provider giả hoặc điểm tạo ngẫu nhiên.
