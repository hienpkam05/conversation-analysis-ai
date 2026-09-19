# Checklist chất lượng 005

- [x] Qdrant payload không chứa PII hoặc profile text.
- [x] Query recruiter nhận danh sách eligible IDs từ hard filter.
- [x] Không hardcode dimension trong Qdrant service.
- [x] Rebuild không tạo duplicate `embedding_refs`.
- [x] Collection reset sẽ trigger rebuild toàn bộ object.
- [x] Integration test collection/upsert/filter pass.
