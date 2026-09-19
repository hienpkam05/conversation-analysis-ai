# Nghiên cứu 006

Hard filter chạy trước Qdrant để các slot Top-N không bị chiếm bởi recruiter inactive, đầy workload hoặc sai vùng. Qdrant chỉ cung cấp tín hiệu semantic; final score luôn kết hợp campaign fit, performance và workload.

Score cosine của Qdrant được chuẩn hóa bằng `clip((raw + 1) / 2, 0, 1)` trước weighted sum. Lý do gợi ý dùng template thay vì LLM để có tính tái lập cho NCKH và dễ kiểm thử.

Frontend gọi matching service qua Vite proxy `/matching-api`, tách biệt proxy `/api` đang phục vụ Django transcribe.
