# Đặc tả 004: Profile và Embedding Provider

## Mục tiêu

Tạo profile text quyết định, không chứa PII, cùng abstraction embedding để thử nghiệm PhoBERT hoặc Sentence-Transformers mà không làm thay đổi pipeline nghiệp vụ.

## Phạm vi

- Dựng profile deterministic cho candidate, recruiter và campaign.
- Tính `profile_hash = SHA-256(normalized_profile_text + model_version_id)`.
- Thêm `EmbeddingProvider` interface.
- Thêm `PhoBERTProvider`: tokenizer + backbone + masked mean pooling + L2 normalization.
- Thêm `SentenceTransformerProvider` để phục vụ so sánh thực nghiệm.
- Chọn provider, model, thiết bị, batch size và max length từ environment.

## Ngoài phạm vi

- Chưa tạo collection, upsert hay query Qdrant: thuộc Đặc tả 005.
- Chưa có endpoint matching, re-ranking hay persistence matching run.
- Không tải mô hình khi API khởi động; provider chỉ tải lazy khi thực sự encode.

## Ràng buộc dữ liệu

- Không đưa `full_name`, `phone`, email, tuổi, giới tính hay địa chỉ chi tiết vào profile/vector/payload.
- Candidate profile chỉ dùng vùng, công việc mong muốn, kinh nghiệm và lương kỳ vọng.
- Recruiter profile chỉ dùng chuyên môn, vùng phụ trách và tên chiến dịch active.
- Campaign profile chỉ dùng vị trí, địa điểm, yêu cầu, phúc lợi và khoảng lương.

## Tiêu chí chấp nhận

- Cùng đối tượng và `model_version_id` tạo cùng text/hash.
- Đổi `model_version_id` làm đổi hash.
- Profile không chứa PII.
- Provider factory chọn đúng provider mà chưa tải model.
- PhoBERT đọc dimension từ backbone, không hardcode dimension trong logic matching.
