# Biên bản tích hợp E ngày 2026-10-19

## Phạm vi thực tế

Đã triển khai hàng đợi AI, API quyền/idempotency, provider local theo hợp đồng manifest, worker process con một slot/timeout/lease, hiển thị tiến độ/lỗi và bản sửa thủ công giữ snapshot AI. Không có checkpoint chất lượng tư vấn đã train hoặc nhãn thật được duyệt. T021–T025 đánh dấu phần code đã triển khai/kiểm thử; T026/AC-08 vẫn mở.

## Migration và dữ liệu

Migration 0007 bổ sung AssessmentJob, QualityWorkerSlot (seed hàng id=1) và inference_metadata. Đã áp dụng trên database SQLite Django. Sao lưu trước E: data/quality_dataset/backups/before-e-2026-10-19.sqlite3, được Git ignore.

Sau kiểm thử và dọn fixture: giữ 20 audio/20 hội thoại/20 revision/325 lượt nói; 0 assessment, 0 job, 0 nhãn approved. Rubric quality-draft-v2 vẫn draft; không tạo tài khoản/mật khẩu mặc định. Không sửa nguồn audio hoặc PostgreSQL matching.

## Kiểm thử code

```powershell
venv\Scripts\python.exe -X utf8 backend\manage.py test consultation_quality --noinput
venv\Scripts\python.exe -X utf8 backend\manage.py makemigrations --check --dry-run
venv\Scripts\python.exe -X utf8 backend\manage.py check_quality_storage
cd frontend
npm.cmd run build
```

68 tests Django đã qua (47 trước E + 21 kiểm thử job/inference), Vue build qua, không phát sinh migration thiếu. Kiểm thử migration nâng từ schema 0004 lên 0007 và giữ snapshot cũ. Storage đọc/ghi/rollback và số bảng con khớp snapshot.

Unit tests dùng provider mock trong database test riêng: queue limit/idempotency, quyền người gửi/người duyệt, rubric mismatch/thiếu model/manifest lỗi, một slot, progress, timeout terminate, lease hết hạn, thu hồi quyền trong lúc chạy, model load/inference lỗi, output NaN/evidence tự tạo, hội thoại quá dài, cửa sổ giữ phần cuối, AI immutable/manual copy/hoàn tất/duyệt riêng. Không có điểm fixture lưu vào database thật sau test. Đây không phải bài đo chất lượng model.

## Kiểm thử trình duyệt và worker

Playwright + Edge headless, frontend Vite 5174 → Django 8000, viewport desktop 1440×1000 và mobile 390×844:

- Đăng nhập qua session/CSRF, mở audio thật call_0387; thiếu model hoặc transcript chưa duyệt thì nút AI bị khóa.
- Tạo hội thoại/job tổng hợp có tiền tố QA007-AI riêng; mở queued, quan sát polling; rời tab KeepAlive dừng polling, quay lại tiếp tục.
- Chạy management command run_quality_worker --once thật với multiprocessing spawn. Process con gặp QUALITY_MODEL_UNAVAILABLE, job failed, không tạo assessment; UI hiện mã lỗi và dừng polling.
- Sau đó tạo snapshot AI tổng hợp riêng chỉ để test hiển thị success/manual-copy; không chạy model giả trong runtime. Mở kết quả, tạo manual draft, chọn dẫn chứng đủ năm mục, hoàn tất thành needs_review. Kiểm tra AI gốc total=null/evidence rỗng không đổi, manual có điểm/tổng và supersedes đúng.
- Không có pageerror; mobile body=390, không tràn ngang. Đã xem screenshot. Toàn bộ fixture job/assessment/conversation/user được xóa theo đúng tiền tố và chủ sở hữu; không xóa dữ liệu thật.

Script/screenshot/result local nằm dưới data/quality_dataset/browser/quality-ai-check.cjs, ai-desktop.png, ai-mobile.png, ai-correction-mobile.png, ai-browser-result.json. File chứa ngữ cảnh local được Git ignore.

## Chưa xác minh

- Chưa load tokenizer/trọng số thật, chưa chạy successful inference thật hoặc đo tài nguyên CPU/VRAM/calibration/F1.
- Chưa chốt hợp đồng cửa sổ/tổng hợp bằng thực nghiệm D; chưa có checkpoint đúng định dạng do D xuất.
- Chưa nghiệm thu deployment Internet, worker nhiều máy hoặc PostgreSQL quality.
- Kiểm tra Docker trực tiếp bị chặn quyền; yêu cầu escalation không thực thi do bộ duyệt tự động không khả dụng. Không khẳng định nội dung database Docker. Theo cấu hình repo, Docker PostgreSQL/Qdrant phục vụ matching, quality vẫn là SQLite Django.

## Kết luận

Hạ tầng E dùng được để kiểm thử điều phối, lỗi và màn hình. Khi chưa có checkpoint được train/đánh giá/duyệt, model-status vẫn available=false và không nhận chấm AI thật. AC-01–AC-05/AC-07 đã có bằng chứng luồng thủ công và cổng model thiếu; AC-06 kiểm tra bằng fixture cần xác nhận tiếp với model thật; AC-08 chưa đạt điều kiện. Không đánh dấu toàn Spec 007 hoàn tất.
