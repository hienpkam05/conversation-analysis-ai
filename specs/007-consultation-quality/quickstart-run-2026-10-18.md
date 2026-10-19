# Biên bản 007 ngày 2026-10-18

Trạng thái: hoàn tất bản local và đợt STT 20 audio mẫu. Chưa huấn luyện hoặc phê duyệt nhãn.

Đã đối chiếu cấu trúc spec 006, API STT Django và phần đề xuất ViDeBERTa trong ảnh tài liệu. File Word hiện có chỉ mô tả bài toán matching nên bộ tiêu chí của Spec 007 được ghi rõ là đề xuất cần duyệt.

Đã tạo app consultation_quality, áp dụng migration vào SQLite Django và mở tab Vue Đánh giá tư vấn. Đã đăng ký 20 mẫu từ manifest local, phát audio bằng ID và giữ bản gốc tại chỗ.

## Kiểm tra đã chạy

- `venv\Scripts\python.exe backend\manage.py test consultation_quality`: 18 tests qua.
- `npm.cmd run build` trong frontend: thành công.
- `manage.py makemigrations --check --dry-run`: không thiếu migration.
- Playwright trên Edge headless, desktop 1440×1000 và mobile 390×844: phát audio thật, lưu nháp, gán vai/chọn dẫn chứng, gửi chờ duyệt, tải lại trang, sửa revision, xem lại bản cũ và giữ điểm khi tách lượt. Không có lỗi JavaScript hoặc tràn ngang.
- Dữ liệu giả do browser test tạo đã xóa khỏi database; không dùng nhãn giả cho các mẫu thật.

## Nhận dạng audio

Model STT: faster-whisper large-v3, checkpoint local `edaa852ec7e145841d8ffdb056a99866b5f0a478`, CPU int8, 8 threads, beam_size=1, temperature=0, VAD bật, condition_on_previous_text=false. Mẫu đầu chạy từng đoạn; các mẫu dài còn lại dùng BatchedInferencePipeline batch_size=4. Metadata từng cuộc lưu cách chạy và thời gian thực tế. Không tải model mới và không gửi audio ra ngoài.

Đầu ra là transcript máy, role=unknown và chưa được người chấm xác nhận. Heuristic review_flags gợi ý đoạn cần nghe lại, không tự xóa hoặc kết luận lời thoại sai. File JSON đối chiếu nằm trong data/quality_dataset và được Git ignore.

Chưa nghiệm thu chất lượng nhận dạng hoặc model chấm điểm AI. Các mục rubric đã duyệt, người chấm sửa/gán vai, gán nhãn pilot và fine-tune trong tasks vẫn để chưa hoàn thành.

## Kết quả cuối đợt mẫu

- 20/20 mẫu hoàn tất, không còn pending/running/failed.
- 19 mẫu có transcript máy, 1 mẫu chưa phát hiện lời nói; tổng 325 đoạn chưa được người chấm xác nhận.
- 9 cuộc có tổng 21 đoạn được heuristic gắn cờ cần nghe đối chiếu; không khẳng định cả 21 đoạn sai và không tự xóa.
- Chưa có assessment nào trên 20 mẫu thật, chưa có nhãn đã duyệt. Dữ liệu giả dùng kiểm thử đã xóa.
- Đã xuất lại đủ 20 mẫu vào `data/quality_dataset/review-transcripts.json`, purpose=human_review_only, approved_for_training=false.
- Phép thử trình duyệt cuối mở `call_0424` dài 1068,912 giây, 40 đoạn: tải metadata audio, tua đến 75% thời lượng, mở transcript, desktop/mobile và tình huống mất kết nối API đều qua. Không có lỗi JavaScript; mobile có scrollWidth=390 bằng viewport=390.

Các kết quả này chứng minh luồng lưu, phát audio và chuẩn bị transcript chạy được; không phải kết quả WER, F1 hoặc đánh giá chất lượng tư vấn tự động.
