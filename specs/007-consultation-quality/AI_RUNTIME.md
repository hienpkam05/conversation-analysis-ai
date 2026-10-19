# Chạy luồng chấm AI của Spec 007

Cập nhật 2026-10-19. Đã có hàng đợi, worker, provider local và giao diện theo dõi. **Chưa có checkpoint chất lượng tư vấn đã train/đánh giá/phê duyệt.** Vì vậy máy hiện tại vẫn báo model chưa sẵn sàng, không sinh điểm AI. Không đặt approved_for_use=true cho model nền hoặc model thử để vượt cổng này.

## Phân biệt database

Quality đang dùng SQLite `backend/db.sqlite3` theo Django settings; PostgreSQL và Qdrant trong `matching_service/docker-compose.yml` phục vụ matching. Container đang chạy không đồng nghĩa đã có nhãn chất lượng tư vấn. Lệnh `quality_training_status` đọc đúng database quality đang cấu hình. Trong đợt này quyền Docker không cho kiểm tra trực tiếp container, nên chưa khẳng định dữ liệu trong PostgreSQL thực tế có gì. Không tự sửa `.env` hoặc chuyển database.

## Chạy web và worker

Từ gốc dự án:

```powershell
venv\Scripts\python.exe -X utf8 backend\manage.py migrate
venv\Scripts\python.exe -X utf8 backend\manage.py runserver 127.0.0.1:8000
```

Terminal khác:

```powershell
cd frontend
npm.cmd run dev
```

Worker là terminal riêng, dùng cùng settings/database và cấu hình checkpoint với Django:

```powershell
venv\Scripts\python.exe -X utf8 backend\manage.py run_quality_worker
```

`--once` chỉ kiểm tra hàng đợi và xử lý tối đa một job rồi thoát. Không cần chạy worker liên tục khi chưa có model. Không tạo job giả để thử trên dữ liệu thật. Chưa cần Redis/Celery cho bản local một slot này.

Khi đã có checkpoint đúng định dạng được người phụ trách duyệt, đặt biến môi trường trong **cả terminal Django và terminal worker**, trước khi khởi động:

```powershell
$env:QUALITY_MODEL_DIR = "D:\NCKH\models\quality\TEN_PHIEN_BAN_DA_DUYET"
```

Không dùng đường dẫn checkpoint Whisper/PhoBERT hoặc chỉ thư mục ViDeBERTa nền. Mặc định biến rỗng, AI bị khóa. Restart Django/worker sau khi thay settings; chỉ refresh Vite không reload Python server `--noreload`.

## Luồng trên web

1. Đăng nhập, mở hội thoại, kiểm tra transcript và vai trò, lưu. Chọn rubric approved khớp checkpoint.
2. Khung Chấm AI đọc model-status nhưng không tải trọng số. Khi thiếu model/rubric chưa duyệt/nội dung chưa kiểm tra/còn sửa chưa lưu, nút gửi bị khóa.
3. Khóa bản và chấm AI seal revision nếu cần rồi POST job. Mỗi yêu cầu có UUID request_key; mạng lỗi không tự gửi thêm job. Cùng revision/rubric/model đang chạy sẽ tái sử dụng job của tài khoản đó.
4. Hiển thị Chờ worker → Đang chấm AI → thành công/chưa hoàn tất. Progress là số cửa sổ đã xử lý, không phải phần trăm độ chính xác. Rời tab/đổi revision/đăng xuất sẽ dừng và hủy request theo dõi. Quay lại tải trạng thái từ server. Poll lỗi thì dừng, người dùng bấm Cập nhật trạng thái AI; không tự tạo job thay thế.
5. Kết quả thành công là snapshot nguồn model, needs_review. Điểm dưới ngưỡng được giữ null và có lý do cần kiểm tra. Không có bộ chọn dẫn chứng tự động đã nghiệm thu, nên evidence rỗng, total_score=null, mọi kết quả cần người duyệt. Không biến softmax thành tỷ lệ đúng.
6. Tạo bản thủ công từ AI, đối chiếu nội dung, sửa điểm/chọn dẫn chứng/ghi lý do. Bản mới dùng source=manual và supersedes liên kết bản trước; model/probabilities gốc không bị ghi đè. Hoàn tất rồi người phụ trách khác duyệt theo quy tắc A/B. API không cho duyệt trực tiếp bản model.

## Worker và giới hạn local

- Job lưu queued/running/succeeded/failed; giữ người gửi, revision/rubric hash, manifest hash, model/preprocessing version, thời gian, lỗi và progress.
- Một slot chung trong database; mặc định timeout 900 giây, tổng tối đa 20 job queued/running, tối đa 2 mỗi người. Cấu hình tại Django settings. Chỉ một process con xử lý model mỗi slot; không giữ transaction trong lúc suy luận.
- Process supervisor dùng spawn, kết thúc process con khi timeout. Job thất bại không có assessment thành công một phần và không tự retry. Người dùng chủ động gửi yêu cầu mới sau khi xử lý nguyên nhân.
- Lease bảo vệ kết quả khi worker bị ngắt. Khi worker mới lấy lease đã hết hạn, job running cũ được đánh dấu WORKER_INTERRUPTED; worker cũ không được công bố kết quả sau khi mất slot. Nếu supervisor bị cưỡng chế dừng, nên xác nhận process con cũ đã dừng trước khi khởi động lại để tránh cạnh tranh tài nguyên ngoài database. Chưa nghiệm thu nhiều máy/worker phân tán.
- Kiểm tra quyền trước và sau suy luận; thu hồi quyền/chặn user khiến job không công bố dữ liệu. Chỉ chủ job và người phụ trách được xem trạng thái/kết quả, dù người khác cũng được giao cùng hội thoại.
- Lỗi trả mã và thông điệp cố định; không đưa text/đường dẫn/trace từ thư viện ML ra response/log ứng dụng. Không gửi audio/transcript lên API ngoài.

## Hợp đồng checkpoint local

Provider hiện thực có chủ đích hẹp: CPU, DeBERTa-v2 encoder từ config + 5 Linear(hidden_size,3), pooling token đầu, tổng hợp trung bình softmax các cửa sổ. State dict safetensors phải có tên `encoder.*`, `heads.<criterion_code>.weight/bias` đúng kiến trúc; strict load không cho phép đầu ngẫu nhiên do thiếu trọng số. Đây là hợp đồng runtime đề xuất cho pipeline D sau này, chưa phải một checkpoint đã nghiệm thu.

File `quality-manifest.json` bắt buộc:

| Trường | Nội dung |
| --- | --- |
| format | `quality-videberta-five-head-v1` |
| model_version | Mã checkpoint duy nhất |
| preprocessing_version | `role-prefix-token-windows-mean-prob-v1` |
| rubric_version/rubric_hash | Phiên bản và SHA256 definitions(version,criteria,general_rules) đúng rubric |
| approved_for_use | Chỉ true sau đánh giá và phê duyệt thật |
| approved_by/approved_at | Người phụ trách và thời điểm ISO |
| evaluation_sha256 | SHA256 báo cáo nghiệm thu model |
| criteria | Năm mã đúng rubric, thứ tự ổn định |
| confidence_thresholds | Object code → ngưỡng 0..1 đã chọn từ validation và được duyệt |
| max_length/overlap_tokens/max_windows | Giới hạn token, chồng lấn và số cửa sổ đã thực nghiệm |
| files | Object tên file local → SHA256; ít nhất config.json, tokenizer.json, quality.safetensors |

Tên file không chứa thư mục/đường dẫn vượt root. Bổ sung tokenizer_config.json, special_tokens_map.json và các file tokenizer cần thiết vào `files` khi xuất model. Worker kiểm tra hash từng file trước khi load; GET status chỉ đọc metadata và sự tồn tại file, không mở trọng số để băm hoặc import torch. available=true nghĩa cấu hình/dependency có vẻ sẵn sàng, không phải đã benchmark thành công.

Tokenizer local-only, trust_remote_code=false, dùng tokenizer đã xuất cùng model. Tiền xử lý nối lượt có tiền tố Tư vấn viên/Ứng viên và xuống dòng; tokenization không truncate. Chia token windows có special tokens, giữ phần cuối; vượt max_windows trả INPUT_TOO_LARGE thay vì cắt âm thầm. Chưa có so sánh thực nghiệm để xác nhận cách tổng hợp này tốt nhất; D cần train/evaluate đúng hợp đồng hoặc tạo format mới.

Manifest do quản trị máy cài đặt, không phải chữ ký số và không được nhận qua body API. Không coi việc điền tên người duyệt/hasher là chứng minh pháp lý hoặc chất lượng model. Pin dependency/commit/tokenizer và giấy phép vẫn thuộc D/T017; máy hiện tại chưa cài bộ torch/transformers/safetensors cho runtime.

## Nghiệm thu còn chờ

Đã kiểm thử điều phối/API/UI và nhánh thất bại local; các unit test dùng provider mock chỉ trong database test. Chưa smoke test load/trọng số/tokenizer thật, chưa xác minh độ chính xác, calibration hay AC-08. Không đánh dấu toàn Spec 007 hoặc T026 xong trước khi có rubric/nhãn/model/báo cáo/ngưỡng được duyệt.
