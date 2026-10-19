# Biên bản A/B ngày 2026-10-19

## Phạm vi

Hoàn thiện nền tảng dữ liệu/API thủ công (B) và công cụ chốt nghiệp vụ (A). Không nghe/gán nhãn giả cho audio thật, không train, không chạy AI chất lượng.

## Thay đổi đã áp dụng

- Migration 0005 chuẩn hóa dữ liệu và backfill snapshot, thêm rubric version, tác giả/người duyệt, owner/members, revision number/hash/seal, điểm/dẫn chứng và biên bản pilot.
- Migration 0006 nguồn hội thoại và tham chiếu call_id. Không đưa đường dẫn audio/token vào trường tham chiếu công khai.
- Sao lưu SQLite trước migration tại `data/quality_dataset/backups/before-governance-2026-10-19.sqlite3`; file local được Git ignore, không đưa dữ liệu lên Git.
- Session/CSRF, phân quyền hội thoại/audio, chấm độc lập và duyệt có danh tính. Không tạo mật khẩu mặc định.
- Vue có đăng nhập, quản lý rubric, đối chiếu chấm kép, biên bản thống nhất, chốt rubric và duyệt từng nhãn. Có hướng dẫn ba tài khoản tại quickstart.md.

## Lệnh kiểm thử

```powershell
venv\Scripts\python.exe -X utf8 backend\manage.py migrate --noinput
venv\Scripts\python.exe -X utf8 backend\manage.py check_quality_storage
venv\Scripts\python.exe -X utf8 backend\manage.py test consultation_quality --noinput
venv\Scripts\python.exe -X utf8 backend\manage.py makemigrations --check --dry-run
cd frontend
npm.cmd run build
```

31 tests Django đã qua, gồm 19 kiểm thử trước đó, 11 kiểm thử quyền/nghiệp vụ và một kiểm thử migration từ 0004 sang 0006. Migration fixture có hai revision cùng hội thoại và assessment legacy; giữ JSON/điểm, tạo bảng con, đánh số đúng và không bịa người chấm/duyệt.

Storage kiểm tra đọc/ghi/rollback thành công, bảng con khớp số snapshot; dung lượng trống khoảng 122,54 GB tại lúc kiểm tra. Dùng SQLite Django, không thay cấu hình PostgreSQL matching. Makemigrations không có thay đổi; Vue build qua.

Playwright/Edge headless chạy giao diện thật qua Vite và Django, không mock endpoint: đăng nhập + CSRF, đọc 20 mẫu, tải metadata audio call_0387, tạo hội thoại tổng hợp riêng, gán vai/xác nhận/chọn dẫn chứng năm tiêu chí, gửi chờ duyệt, reload/mở lại, chặn duyệt rubric 0/3, kiểm tra desktop 1440×1000/mobile 390×844, logout rồi API trả 401. Không có lỗi JavaScript; body mobile=390, không tràn ngang. Ảnh/result/script lưu dưới `data/quality_dataset/`, được ignore. Tài khoản/hội thoại/assessment tổng hợp đã xóa sau test, không sửa bản chấm của audio thật.

Kiểm thử đơn vị dùng database test riêng để chạy đủ ba cặp chấm, xử lý bất đồng, chốt rubric và duyệt nhãn. Đây là fixture kiểm tra code, không phải bằng chứng chốt rubric thật. Chưa thực hiện ba người chấm thật trên web hay đo độ đồng thuận người chấm.

## Dữ liệu thật sau kiểm tra

- 20 Conversation, 20 AudioSample, 20 Revision, 325 Utterance.
- 19 ready, 1 no_speech; giữ đường dẫn và audio gốc.
- 0 Assessment, 0 PilotResolution, 0 nhãn được duyệt.
- quality-draft-v2 vẫn draft; không có tài khoản mặc định/fixture còn lại.

T004–T009 được đánh dấu theo phần đã triển khai. T001/T003/P007/P011 còn mở chờ nghe/sửa/chấm kép/duyệt thật. D/E không đánh dấu hoàn tất.
