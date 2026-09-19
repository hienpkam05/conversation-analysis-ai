# Checklist chất lượng 004

- [x] Không chứa `full_name` hoặc `phone` trong profile text.
- [x] Profile có thứ tự ổn định cho region và campaign.
- [x] Provider không tải model tại thời điểm khởi tạo.
- [x] Không hardcode vector dimension trong profile/matching logic.
- [x] PhoBERT có mean pooling theo attention mask và L2 normalization.
- [x] Có lựa chọn Sentence-Transformers phục vụ baseline.
