# Kế hoạch 004

1. Bổ sung cấu hình embedding vào Pydantic Settings.
2. Tạo builder chuẩn hóa whitespace, dựng profile và hash ổn định.
3. Tạo interface provider, factory và hai implementation PhoBERT/Sentence-Transformers.
4. Đặt dependency ML vào extra `embeddings` để Docker API nền không phải tải PyTorch khi chưa chạy semantic retrieval.
5. Viết unit test profile và factory; xác nhận service hiện hữu không bị ảnh hưởng.

## Quyết định kỹ thuật

- PhoBERT dùng masked mean pooling trên token hợp lệ, sau đó L2 normalize để dùng cosine similarity ở Qdrant.
- Model được tải lazy và giữ singleton theo instance provider; không tải lại ở mỗi lần `encode`.
- Dimension lấy từ `model.config.hidden_size` hoặc `get_sentence_embedding_dimension()`.
- Collection/Qdrant chỉ được tạo khi Spec 005 đã biết dimension thực tế của provider.
