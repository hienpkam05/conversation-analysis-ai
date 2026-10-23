# Chạy tóm tắt và lịch hẹn

Từ D:\NCKH, dùng cùng môi trường đã chạy Django:

```powershell
venv\Scripts\python.exe -X utf8 backend\manage.py migrate
venv\Scripts\python.exe -X utf8 backend\manage.py runserver 127.0.0.1:8000
```

Terminal thứ hai:

```powershell
cd frontend
npm.cmd run dev
```

Mở URL Vite in ra, chọn **Tóm tắt & lịch hẹn**, đăng nhập bằng tài khoản đã được cấp quyền ở 007. Không cần worker AI, Docker matching hoặc model tóm tắt cho bản trích dẫn này.

## Cấu hình đang dùng trên máy này

Cổng 8000 đang có dịch vụ khác, nên lần kiểm thử này dùng Django **8002** và Vue **5175**. File `frontend/.env.local` (không đưa lên Git) đã cấu hình:

```dotenv
VITE_DJANGO_API_URL=http://127.0.0.1:8002
VITE_CACHE_DIR=../.cache/vite-frontend-followup
```

Khởi động lại theo cấu hình này:

```powershell
venv\Scripts\python.exe -X utf8 backend\manage.py runserver 127.0.0.1:8002
```

Ở terminal khác, trong `frontend`:

```powershell
npm.cmd run dev -- --host 127.0.0.1 --port 5175 --strictPort
```

Mở `http://127.0.0.1:5175`. Khi đổi cổng Django, sửa `VITE_DJANGO_API_URL` tương ứng và khởi động lại Vite. Máy clone chưa có `.env.local` vẫn dùng backend 8000 theo mặc định.

## Thử luồng nghiệp vụ

1. Chọn hội thoại và phiên bản, bấm Tạo tóm tắt trích dẫn. Mỗi ý có Nguồn để nghe/đối chiếu. Transcript chưa kiểm tra chỉ tạo bản xem trước.
2. Muốn sửa: Tạo bản sửa thủ công, thay nội dung/chọn bằng chứng rồi Lưu tóm tắt. Mỗi ý cần ít nhất một nguồn, không thêm dữ kiện không có căn cứ.
3. Đã đối chiếu nội dung với lời thoại → Duyệt tóm tắt. Nếu báo transcript chưa kiểm tra, quay về Đánh giá tư vấn để sửa/gán vai/xác nhận rồi tạo tóm tắt trên revision mới. Không cần chấm/duyệt nhãn chất lượng 007 để dùng 008.
4. Nhập lịch nháp; ngày giờ hiển thị giờ Việt Nam. “Mai/tuần sau” trong câu nguồn không tự điền vào form. Không chắc ngày thì để nháp và xác nhận lại với người tham gia.
5. Chọn lời đối chiếu lịch từ cả hai bên; Lưu lịch nháp. Chỉ tích Đã thống nhất lịch với người tham gia khi đã kiểm tra thật, rồi Xác nhận lịch.
6. Xem Lịch hẹn nội bộ. Mở draft để sửa, hoặc Hủy lịch. Lịch đã xác nhận không sửa tại chỗ; hủy và tạo lịch mới. Không có email/SMS/lời mời calendar được gửi.

Tài khoản chỉ đọc/sửa được dữ liệu trong phạm vi được giao; người tạo hoặc người phụ trách mới sửa/duyệt/xác nhận/hủy bản ghi. Đăng nhập/đăng xuất làm mới cache cả hai workspace để không giữ dữ liệu tài khoản trước.
