# Nghiên cứu 005

Collection có suffix model/version vì vector của model mới có thể khác dimension. Khi dimension không khớp, service dừng với lỗi rõ ràng thay vì ghi lẫn vector vào collection cũ.

Qdrant chỉ là tầng retrieval. Workload, status và điều kiện campaign động vẫn do PostgreSQL hard filter quyết định trước. Query vector bắt buộc filter theo `eligible_recruiter_ids`; không được lấy toàn bộ Top-N rồi mới loại ở application.

`profile_hash` kết hợp `model_version_id` giúp rebuild có thể bỏ qua object không đổi. Khi collection mới tạo, service re-embed toàn bộ object hợp lệ để chống tình huống Qdrant vừa bị reset.
