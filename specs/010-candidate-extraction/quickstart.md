# Dùng thông tin ứng viên và gợi ý chiến dịch

## Khởi động local

Từ D:\NCKH:

```powershell
venv\Scripts\python.exe -X utf8 backend\manage.py migrate
venv\Scripts\python.exe -X utf8 backend\manage.py runserver 127.0.0.1:8002
```

frontend/.env.local trên máy hiện tại trỏ VITE_DJANGO_API_URL=http://127.0.0.1:8002; máy clone mặc định dùng 8000, cần đồng bộ cổng hoặc tạo cấu hình local tương ứng. Terminal khác:

```powershell
cd frontend
npm.cmd run dev -- --host 127.0.0.1 --port 5175 --strictPort
```

Mở http://127.0.0.1:5175 → **Thông tin & chiến dịch**. Dùng tài khoản 007 đã có quyền và được giao hội thoại; không có mật khẩu mặc định. Không cần model NER/Colab để dùng bản quy tắc và sửa thủ công.

Sau lượt triển khai ngày 23/10/2026, web/Django/matching trên các cổng trên đã được bật để dùng thử; không cần mở thêm một server trên cùng cổng khi chúng còn chạy.

## Chuẩn bị Matching Service

```powershell
cd matching_service
docker compose up --build -d
Invoke-RestMethod http://127.0.0.1:8001/api/v1/health
```

Dependency embedding cần INSTALL_EMBEDDINGS=true trong .env. Lần đầu build/tải checkpoint có thể lâu; xem README dự án để cài matching. Sau thay đổi code API, cần rebuild image, không chỉ refresh trình duyệt. Không chạy down -v vì lệnh đó xóa volume dữ liệu.

Chiến dịch phải có dữ liệu PostgreSQL active/nondeleted, model version khớp config và vector hiện hành. Khi cần cập nhật vector từ chiến dịch đã có:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8001/api/v1/embeddings/campaigns/rebuild
```

Lệnh rebuild tính lại vector và cập nhật embedding refs; không cần gọi mỗi lần tìm. Nếu chưa có chiến dịch thật, nhập qua luồng quản trị nghiệp vụ hiện có; không coi dữ liệu demo là dữ liệu tuyển dụng thật. Bản 010 không tự seed.

Django dùng MATCHING_API_URL mặc định http://127.0.0.1:8001. Khi chạy Django trong container khác phải cấu hình địa chỉ service tương ứng; URL không nhập từ client. Không trỏ server thật vào Postman simulation.

## Thao tác

1. Chọn hội thoại/revision, nghe nguồn. Nếu vai/transcript chưa kiểm tra, xử lý ở tab Đánh giá tư vấn trước.
2. Trích xuất thông tin. Mỗi trường có Nguồn; trống nghĩa chưa đủ căn cứ, không có nghĩa ứng viên không có thông tin đó.
3. Tạo bản sửa thủ công, sửa giá trị và chọn lời ứng viên làm căn cứ. Chọn lại option nếu xung đột; có thể để trống trường chưa rõ. Vùng muốn làm chọn thủ công có dẫn chứng, không mặc định theo nơi ở.
4. Lưu bản thông tin, đối chiếu và Xác nhận thông tin. Lịch sử/bản quy tắc gốc được giữ; xác nhận sẽ khóa revision, sửa nguồn cần revision mới.
5. Chọn số kết quả. Vùng muốn làm được lọc cứng khi có; lọc lương cứng là tùy chọn và cần lương VND/tháng đã xác nhận. Khi bật, chiến dịch thiếu salary_max không được coi là thỏa.
6. Kiểm tra nội dung nghề nghiệp và xác nhận gửi để tìm. Các trường tên/phone/nơi ở/full transcript không được gửi; văn bản nghề nghiệp vẫn cần rà thông tin riêng tư.
7. Xem cosine, lương, địa điểm, yêu cầu và cảnh báo. Ca/ngày bắt đầu cần hỏi lại; chưa có hồ sơ/gán chiến dịch tự động. Có lịch sử query/kết quả theo thời điểm tìm, không đảm bảo dữ liệu chiến dịch không thay đổi sau đó.

## Kiểm thử

```powershell
venv\Scripts\python.exe -X utf8 backend\manage.py test consultation_quality conversation_followup candidate_status candidate_info --noinput
```

Trong môi trường matching đã cài dependency dev:

```powershell
cd matching_service
python -m pytest tests -q -k "not trio"
```

Bỏ qua backend trio tùy chọn khi chưa cài trio. Qdrant integration cần TEST_QDRANT_URL riêng, không dùng collection nghiệp vụ cho test ghi/xóa.

Postman simulation fixture theo đúng contract để kiểm tra HTTP lỗi, **không phải API thật**:

```powershell
postman simulation run postman/simulations/candidate-info.sim.yaml --port 4930 --output ndjson --no-history
```

Base test http://127.0.0.1:4930/matching; chỉ dùng với database kiểm thử tách biệt và dữ liệu giả. __test_mode là route điều khiển lỗi dành riêng fixture, không có ở matching thật. Log simulation có thể ghi body nên không gửi dữ liệu cá nhân. Chi tiết kết quả ở báo cáo chạy.
