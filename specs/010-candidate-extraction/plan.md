# Kế hoạch 010

## Tái sử dụng

Django: session/CSRF, quyền annotate_quality/review_quality, Conversation/Revision và luồng nghe/kiểm tra nguồn 007. Vue: tab riêng, cache theo session chung. Matching: kho Campaign PostgreSQL, model version/ref, provider embedding và Qdrant đang dùng cho recruiter matching.

## Triển khai bản đầu

1. Định nghĩa trường, schema dẫn chứng, snapshot và hợp đồng tìm chiến dịch.
2. Quy tắc bảo thủ lấy lời ứng viên, giữ mâu thuẫn/thiếu dữ liệu thay vì tự điền.
3. Tạo bản manual riêng và xác nhận đúng nguồn hiện hành; không tự tạo Candidate SQL.
4. API tìm campaign từ query tối thiểu, lọc business trước vector, đối chiếu ref/hash/point/model version.
5. Giao diện sửa/đối chiếu, xác nhận gửi dữ liệu, kết quả và lịch sử.
6. Kiểm thử Django, matching, trình duyệt desktop/mobile và đường HTTP lỗi bằng Postman simulation tách biệt.

## Sau bản đầu

Người dùng nghiệm thu trên audio thật, chuẩn hóa địa điểm/đơn vị lương và trường ca/ngày bắt đầu của Campaign nếu muốn lọc các điều kiện này. Sau đó gán nhãn span/BIO, duyệt và train PhoBERT NER riêng. Không đánh dấu đã train hoặc đã tạo lịch/gán chiến dịch từ baseline.
