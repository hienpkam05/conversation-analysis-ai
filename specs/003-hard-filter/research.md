# Nghiên cứu: Đặc tả 003

Hard filter phải chạy trước Qdrant. Nếu truy vấn toàn bộ recruiter bằng vector rồi mới loại inactive/full/out-of-region, Top-N có thể bị chiếm bởi recruiter không hợp lệ và làm sai kết quả nghiên cứu. Workload thay đổi thường xuyên nên được quyết định từ PostgreSQL.
