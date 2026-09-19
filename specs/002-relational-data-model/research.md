# Nghiên cứu: Đặc tả 002

Schema lấy từ `Bai_toan_1.docx`: PostgreSQL là nguồn dữ liệu nghiệp vụ, còn Qdrant chỉ nhận vector và metadata tối thiểu ở phase sau. Dữ liệu hay thay đổi như workload phải được đọc từ PostgreSQL, không sao chép làm nguồn quyết định sang Qdrant.

Seed dùng UUID xác định từ tên logic để mỗi lần chạy nhận lại cùng ID. Vì vậy script có thể kiểm tra bản ghi đã có và chạy lặp lại an toàn.
