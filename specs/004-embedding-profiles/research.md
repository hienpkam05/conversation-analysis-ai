# Nghiên cứu 004

PhoBERT là backbone tiếng Việt tốt, nhưng không được huấn luyện chuyên biệt cho sentence similarity. Vì vậy nó được giữ như cấu hình thí nghiệm theo hướng NCKH, còn `SentenceTransformerProvider` là baseline embedding có thể so sánh trực tiếp.

Masked mean pooling bỏ token padding trước khi lấy trung bình hidden states. L2 normalization làm vector có độ dài 1, phù hợp với cosine distance và giúp score semantic ở phase sau dễ chuẩn hóa.

Model nặng không nằm trong runtime dependency nền của API. Cài extra `embeddings` khi cần rebuild/query vector giúp Docker phục vụ health, database và hard filter khởi động nhẹ hơn.
