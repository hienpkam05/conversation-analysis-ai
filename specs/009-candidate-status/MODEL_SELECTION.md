# Checkpoint và môi trường ViDeBERTa

Kiểm tra nguồn ngày 23/10/2026:

- Checkpoint tham chiếu: [Fsoft-AIC/videberta-base](https://huggingface.co/Fsoft-AIC/videberta-base). Đây không phải checkpoint phân loại trạng thái ứng viên đã fine-tune.
- [Danh sách file](https://huggingface.co/Fsoft-AIC/videberta-base/tree/main) có trọng số pytorch_model.bin và tokenizer JSON. Script chỉ đọc thư mục local, dùng weights_only=True, trust_remote_code=False; model sau fine-tune lưu safetensors.
- [Model card gốc](https://huggingface.co/Fsoft-AIC/videberta-base/raw/main/README.md) chưa có trường license tường minh tại thời điểm đọc. [Repo tác giả](https://github.com/HySonLab/ViDeBERTa) công bố mã nguồn và [LICENSE](https://github.com/HySonLab/ViDeBERTa/blob/main/LICENSE); không coi giấy phép code tự động xác minh quyền trọng số/dữ liệu. Cần người phụ trách kiểm tra quyền sử dụng trước khi tải/train/phát hành.
- Cách dùng sequence classification theo [tài liệu Transformers](https://huggingface.co/docs/transformers/en/tasks/sequence_classification); script dự án có thêm gộp cửa sổ hội thoại, kiểm soát rò rỉ nhóm và từ chối cắt âm thầm phần cuối.

## Trạng thái hiện tại

Chưa tải checkpoint, chưa cài thư viện ML vào môi trường web, chưa smoke test tokenizer/trọng số hoặc GPU, chưa đo RAM/VRAM. requirements-ml.txt là công thức môi trường riêng, không phải lockfile đã kiểm chứng trên GPU. Cổng giấy phép và kiểm thử model thật chưa đóng.

## Thiết kế phân loại

Năm trạng thái nghiệp vụ cộng một nhãn unknown rõ ràng, tổng cộng 6 đầu ra. Unknown được học từ ví dụ đã duyệt và cũng là kết quả khi xác suất tối đa dưới ngưỡng chọn trên validation. Đây là lựa chọn triển khai cần được người phụ trách duyệt trong taxonomy, không âm thầm biến unknown thành một trong năm trạng thái.

Tiền xử lý dùng vai người nói và văn bản đã che thông tin cơ bản. Bỏ lượt đánh dấu khó nghe, giữ đầy đủ phần văn bản nghe rõ theo cửa sổ token không chồng lấn. Lấy trung bình xác suất cửa sổ ở mức cuộc gọi, tối ưu loss ở mức cuộc gọi; không coi mỗi cửa sổ là một cuộc độc lập và không chia cửa sổ của cùng cuộc sang các tập khác.

Mô hình không trích xuất dẫn chứng đáng tin cậy: đầu ra source=model luôn có evidence_ids rỗng, review_required=true. Người dùng phải tạo bản manual/chọn lời dẫn chứng rồi xác nhận; không tự diễn giải xác suất thành lời giải thích.
