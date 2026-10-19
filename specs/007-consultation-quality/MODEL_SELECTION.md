# Khảo sát checkpoint cho D/T017

Ngày kiểm tra: 2026-10-19. Trạng thái: đề xuất, chưa chốt thực nghiệm hoặc quyền phát hành trọng số.

## Nguồn chính thức

- [Model card Fsoft-AIC/videberta-base](https://huggingface.co/Fsoft-AIC/videberta-base): model nền tiếng Việt; không phải checkpoint đã fine-tune cho năm tiêu chí tư vấn.
- [Config checkpoint](https://huggingface.co/Fsoft-AIC/videberta-base/blob/main/config.json): model_type deberta-v2, hidden_size 768, 12 layers, max_position_embeddings 512. Đây là cấu hình encoder, không phải bảo đảm chạy được toàn bộ hội thoại dài trong một lần.
- [Tokenizer config](https://huggingface.co/Fsoft-AIC/videberta-base/blob/main/tokenizer_config.json): tokenizer_class DebertaV2Tokenizer. Repo còn có tokenizer.json; cần smoke test tokenizer thật trước khi pin môi trường. Không tự thêm bước tách từ PhoBERT sang ViDeBERTa.
- [Repo tác giả HySonLab/ViDeBERTa](https://github.com/HySonLab/ViDeBERTa) hiển thị giấy phép MIT. Model card checkpoint được đọc chưa nêu trường license rõ ràng; không suy diễn giấy phép code đồng nghĩa đã xác minh mọi quyền của trọng số và dữ liệu.

## Quyết định trước khi tải/train

1. Xác nhận bản quyền/quyền sử dụng checkpoint cho mục đích thực tế, pin full commit SHA và lưu checksum các file; chưa xem main là revision tái lập.
2. Tạo môi trường ML riêng phù hợp torch/transformers và GPU thực tế; không thay môi trường Django Python 3.14 chỉ để cố train khi chưa có nhãn.
3. Smoke test AutoTokenizer với trust_remote_code=false, token tiếng Việt, ký hiệu vai trò, độ dài và phần cuối hội thoại. Dùng AutoModel encoder, không pipeline token-classification để giả lập năm điểm.
4. Dùng giới hạn token đã kiểm tra có tính special tokens. Cửa sổ phải bao phủ phần cuối, không tách cửa sổ sang các split khác nhau. So sánh cách tổng hợp trên validation, lưu preprocessing version.
5. Khởi tạo năm đầu ba lớp; nhãn thiếu mask khỏi loss. Đánh giá cấp hội thoại, không sao chép nhãn cuộc gọi thành “sự thật” cho từng cửa sổ rồi báo accuracy cửa sổ.
6. Đo RAM/VRAM, thời gian và lỗi thật. Không lấy con số RAM trong ảnh tài liệu làm cam kết tài nguyên train.

Chưa tải model hoặc chạy fine-tune. Không có checkpoint chất lượng tư vấn mới được sinh ra trong đợt chuẩn bị này. T017 vẫn mở.
