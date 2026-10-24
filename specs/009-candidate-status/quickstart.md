# Dùng phân loại trạng thái ứng viên

## Khởi động

Từ D:\NCKH, dùng môi trường Python đã cài dependency:

```powershell
venv\Scripts\python.exe -X utf8 backend\manage.py migrate
venv\Scripts\python.exe -X utf8 backend\manage.py runserver 127.0.0.1:8002
```

Máy hiện tại có frontend/.env.local (không đưa lên Git):

```dotenv
VITE_DJANGO_API_URL=http://127.0.0.1:8002
VITE_CACHE_DIR=../.cache/vite-frontend-followup
```

Ở terminal khác:

```powershell
cd frontend
npm.cmd run dev -- --host 127.0.0.1 --port 5175 --strictPort
```

Mở http://127.0.0.1:5175, chọn **Trạng thái ứng viên**. Máy clone chưa có cấu hình local thì Vite mặc định nối Django 8000; cần chạy backend đúng cổng hoặc đặt VITE_DJANGO_API_URL rồi restart Vite. Không cần Colab, Qdrant hay worker AI cho tab này.

## Thao tác

1. Đăng nhập tài khoản Spec 007 đã được giao hội thoại hoặc có quyền reviewer. Không có tài khoản/mật khẩu mặc định.
2. Chọn hội thoại và revision. Có thể nghe audio gốc nếu đường dẫn trên máy còn tồn tại.
3. Bấm **Phân loại theo quy tắc** để có bản gợi ý, hoặc **Gán trạng thái thủ công**. Màu xanh ở lời thoại chỉ dẫn chứng đã chọn, không phải confidence.
4. Muốn sửa, bấm **Tạo bản sửa thủ công**, chọn nhãn và checkbox dẫn chứng ở lời ứng viên, thêm nhận định rồi **Lưu bản thủ công**. Unknown cần ghi lý do; nhãn cụ thể cần dẫn chứng ứng viên nghe rõ.
5. Đối chiếu audio/transcript thật, tích xác nhận và **Xác nhận trạng thái**. Nếu nguồn chưa kiểm tra hoặc vai chưa rõ, xử lý ở tab Đánh giá tư vấn trước. Dữ liệu ban đầu chưa được xác nhận hộ.
6. Xem trạng thái hiện hành, người xác nhận và lịch sử. Draft không thay confirmed. Muốn sửa bản đã xác nhận, tạo bản thủ công mới; muốn sửa nguồn đã khóa, tạo revision mới ở tab đánh giá.

Đây là bộ nhãn đề xuất và baseline quy tắc, chưa phải ViDeBERTa. Không tự tạo lịch/loại ứng viên, không tự đổi dữ liệu matching. Dữ liệu lưu trong backend/db.sqlite3, không ở PostgreSQL matching.

## Kiểm thử

```powershell
venv\Scripts\python.exe -X utf8 backend\manage.py test consultation_quality conversation_followup candidate_status --noinput
```

Không đánh đồng test kỹ thuật với đo chất lượng trên cuộc gọi thật. Xem tasks.md phần B cho công việc còn lại.

## Phần B: duyệt nhãn và huấn luyện

Trên web, mục Bộ nhãn và dữ liệu huấn luyện có định nghĩa, form reviewer duyệt bộ nhãn và báo cáo tiến độ. Người gán nhãn tạo bản manual/xác nhận; reviewer khác tác giả mở lại để duyệt nhãn train hoặc từ chối. Bản confirmed chưa duyệt độc lập không được xuất train.

Xem [hướng dẫn gán nhãn](ANNOTATION_GUIDE.md) và [các lệnh xuất/chia/train/duyệt checkpoint](TRAINING.md). Chưa cấu hình model được duyệt thì Phân loại ViDeBERTa bị khóa, không gọi model giả hoặc tự dùng rules thay cho ViDeBERTa.
