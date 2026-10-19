# Đặc tả 007: Đánh giá chất lượng tư vấn tuyển dụng

Ngày tạo: 2026-10-18. Trạng thái: tiêu chí đang nháp để duyệt nghiệp vụ; đã có bản chấm thủ công local, chưa có model chấm AI.

## Mục tiêu và căn cứ

Đánh giá cuộc hội thoại tư vấn tuyển dụng theo 5 tiêu chí, trình bày điểm từng tiêu chí cùng lời thoại làm bằng chứng để người phụ trách xem xét và sửa kết quả.

Ảnh tài liệu định hướng dùng ViDeBERTa Multi-task với 5 đầu phân loại dùng chung bộ mã hóa. File `Bai_toan_1.docx` hiện có chỉ mô tả matching, không xác định 5 tiêu chí đánh giá tư vấn. Vì vậy tên tiêu chí, thang điểm và trọng số dưới đây là đề xuất, cần duyệt trước khi gán nhãn và huấn luyện. Không xem chúng là yêu cầu đã được trích từ tài liệu gốc.

## Phạm vi và thứ tự thực hiện

Giai đoạn A cung cấp luồng dùng được trên web: nhập hội thoại, chỉnh lượt nói và vai trò, chấm thủ công, chọn dẫn chứng, lưu và xem lại. Giai đoạn B bổ sung suy luận ViDeBERTa sau khi có dữ liệu gán nhãn và mô hình đạt điều kiện nghiệm thu. Không sinh điểm giả để thay model chưa có.

Bao gồm dữ liệu đánh giá, phiên bản tiêu chí, API Django, giao diện Vue, quy trình gán nhãn, hợp đồng model và kiểm thử. Không huấn luyện ngay từ đầu khi chưa có tập dữ liệu hợp lệ.

Ngoài phạm vi: cảm xúc ứng viên, NER/gợi ý chiến dịch, tóm tắt/tạo lịch, phân loại trạng thái phỏng vấn; tự động phân biệt giọng nói; thay đổi thuật toán matching; tự động thưởng/phạt nhân viên theo điểm AI.

## Luồng người dùng

1. Mở tab `Đánh giá tư vấn`, nhập hội thoại hoặc chuyển kết quả nhận dạng hiện tại sang bản nháp.
2. Kiểm tra nội dung, tách/gộp lượt nói và gán vai trò `Tư vấn viên`, `Ứng viên`, `Chưa xác định`. Whisper segment không mặc nhiên là một lượt nói hay một người nói.
3. Lưu hội thoại. Các vai trò chưa rõ vẫn được lưu nháp; đánh giá tự động bị chặn đến khi người dùng xác nhận vai trò liên quan.
4. Chấm thủ công và chọn dẫn chứng. Khi model sẵn sàng, có thể yêu cầu đánh giá tự động để so sánh.
5. Xem điểm từng tiêu chí, bằng chứng, mục cần xem lại; người phụ trách có thể sửa điểm trong một bản đánh giá thủ công riêng.
6. Mở lại lịch sử theo hội thoại. Sửa hội thoại tạo phiên bản mới, không làm thay đổi dẫn chứng của kết quả cũ.

## Bộ tiêu chí đề xuất

Định nghĩa chi tiết mức 0/1/2, trường hợp không đủ dữ liệu và ví dụ nằm trong [ANNOTATION_GUIDE.md](ANNOTATION_GUIDE.md). Bản hiện tại là quality-draft-v2, vẫn chưa được duyệt. Chấm thử bằng [PILOT_REVIEW.md](PILOT_REVIEW.md) trước khi mở rộng gán nhãn.

| Mã | Tiêu chí | Nội dung cần kiểm tra |
| --- | --- | --- |
| opening | Mở đầu và xác nhận mục đích | Giới thiệu, xác nhận đối tượng và lý do gọi phù hợp |
| needs | Khai thác nhu cầu | Hỏi/làm rõ khu vực, loại việc, thời gian hoặc điều kiện quan trọng với ứng viên |
| job_information | Cung cấp thông tin công việc | Trình bày rõ công việc và các điều kiện liên quan; chưa kết luận thông tin đúng thực tế nếu không có nguồn đối chiếu |
| interaction | Lắng nghe và giải đáp | Phản hồi đúng câu hỏi, làm rõ băn khoăn, giao tiếp tôn trọng qua nội dung văn bản |
| next_steps | Thống nhất bước tiếp theo | Chốt hành động, cách liên hệ hoặc thời gian tiếp theo rõ ràng |

Mỗi tiêu chí có nhãn `0`: chưa đạt; `1`: đạt một phần; `2`: đạt; `not_assessable`: không đủ dữ liệu để đánh giá. Điểm 0 phản ánh thiếu hành vi trên một bản ghi đủ ngữ cảnh; bản ghi bị cắt/không nghe rõ cần nhãn không đủ dữ liệu, không tự gán 0.

Trọng số đề xuất bằng nhau: 0.20 mỗi tiêu chí. Điểm tổng chỉ có khi cả 5 tiêu chí có điểm và dẫn chứng hợp lệ: `100 × tổng(trọng số × điểm / 2)`. Thiếu bất kỳ tiêu chí nào thì `total_score=null`, hiển thị `Chưa đủ dữ liệu`; không chuẩn hóa lại trọng số để che phần thiếu.

Với điểm 0 vì hành vi không xuất hiện, người chấm đánh dấu `absence` và phạm vi hội thoại đã kiểm tra thay vì bịa một câu làm bằng chứng. Các điểm 1/2 phải dẫn đến ít nhất một lượt nói của tư vấn viên. Nhận xét và khuyến nghị phải gắn với tiêu chí, không viết thêm lời thoại không tồn tại.

## Yêu cầu chức năng

- FR-01: Nhập văn bản và kết quả STT dưới dạng bản nháp; giữ nguồn và ghi nhận nội dung không nghe rõ.
- FR-02: Cho sửa lượt nói, vai trò và thời gian nếu có; xác nhận vai trò là thao tác của người dùng, không suy đoán từ vị trí câu.
- FR-03: Lưu phiên bản hội thoại bất biến đã được dùng để đánh giá; kết quả tham chiếu đúng phiên bản.
- FR-04: Lưu rubric có phiên bản, 5 tiêu chí, thang điểm và trọng số; sửa rubric tạo phiên bản mới.
- FR-05: Chấm thủ công dùng được khi model vắng mặt; sửa kết quả AI tạo bản thủ công liên kết, không ghi đè kết quả gốc.
- FR-06: Kiểm tra score, dẫn chứng, vai trò và phạm vi bằng chứng ở server; trích đoạn hiển thị lấy từ dữ liệu gốc.
- FR-07: Model chưa được cấu hình hoặc chưa qua đánh giá phải được thông báo rõ; không dùng model nền để tạo điểm chất lượng ngẫu nhiên.
- FR-08: Model trả nhãn cho 5 tiêu chí; xác suất model không được trình bày như tỷ lệ đúng. Dưới ngưỡng đã hiệu chỉnh thì cần người xem lại.
- FR-09: Chỉ tính điểm tổng khi đủ dữ liệu; các nhãn không đủ dữ liệu luôn giữ được khi xuất/lưu.
- FR-10: Mọi lần đánh giá lưu nguồn `manual`/`model`, model version, rubric version, phiên bản tiền xử lý, thời gian và trạng thái duyệt.
- FR-11: Xem danh sách và chi tiết đánh giá trên Vue; có trạng thái đang tải, chưa có dữ liệu, model chưa sẵn sàng và lỗi.
- FR-12: Dữ liệu hội thoại không đưa vào Qdrant matching; log không chứa nguyên văn hội thoại hay thông tin liên hệ.

## ViDeBERTa và dữ liệu huấn luyện

Chưa chốt checkpoint ViDeBERTa cụ thể; lựa chọn phải ghi nguồn, giấy phép và khả năng chạy trong môi trường dự án. Chỉ dùng checkpoint đã fine-tune cho rubric, không dùng tên model như bằng chứng độ chính xác.

Mô hình dự kiến dùng chung encoder và 5 đầu phân loại 3 lớp (0/1/2). Nhãn không đủ dữ liệu được mask khỏi loss của tiêu chí tương ứng. Hệ thống kiểm tra dữ liệu và độ tin cậy để trả `not_assessable`/cần duyệt, không ép mọi tiêu chí thành điểm số.

Hội thoại dài được chia thành các cửa sổ có ID lượt nói, giữ ngữ cảnh hai bên và bảo đảm không bỏ phần cuối. Quy tắc kết hợp cửa sổ phải được thử nghiệm, ghi phiên bản và đánh giá trên hội thoại hoàn chỉnh. Encoder phân loại không tự tạo bằng chứng: nếu chưa có cơ chế chọn bằng chứng đã được kiểm chứng, kết quả AI chỉ là nháp, chờ người chọn dẫn chứng rồi mới được duyệt.

Tập dữ liệu chia theo cuộc hội thoại, nhóm theo ứng viên/chuỗi liên hệ nếu có; tuyệt đối không chia các cửa sổ của cùng cuộc gọi vào train và test. Lưu một tập test độc lập, có phân bố điểm và kiểm tra rò rỉ. Đo macro-F1 từng tiêu chí, ma trận nhầm lẫn, tỷ lệ cần duyệt, và độ lệch điểm tổng so với người chấm; không chỉ báo accuracy trung bình.

## Tiêu chí nghiệm thu

- AC-01: Nhập văn bản, sửa vai trò, chấm 5 tiêu chí, lưu và mở lại được trên web mà không cần model.
- AC-02: Chuyển transcript vào đánh giá không mất thứ tự; không tự gán các segment luân phiên thành hai người nói.
- AC-03: Dẫn chứng luôn thuộc phiên bản hội thoại đã chấm; sửa bản nháp mới không đổi kết quả cũ.
- AC-04: Cả 5 tiêu chí bằng 2 cho tổng 100, bằng 0 cho tổng 0; một mục không đủ dữ liệu cho tổng null.
- AC-05: Không có model thì đánh giá tự động trả mã lỗi có ý nghĩa, không ghi thành công hoặc tạo điểm giả.
- AC-06: Model không có bằng chứng/không đủ tự tin chỉ trả bản nháp cần duyệt; người dùng nhìn rõ nguồn và trạng thái.
- AC-07: Kiểm tra thực tế trên desktop/mobile: đọc được từng lượt nói, chọn dẫn chứng, sửa điểm, lưu và xem lịch sử, không tràn nội dung.
- AC-08: Trước khi mở AI cho sử dụng chính thức, phải có rubric đã duyệt, tập test độc lập, báo cáo chỉ số và ngưỡng phát hành được người phụ trách phê duyệt. Chưa đặt mục tiêu F1 giả khi chưa có baseline.

## Các quyết định cần duyệt

- Tên, định nghĩa, ví dụ ranh giới 0/1/2 và trọng số của 5 tiêu chí.
- Khi nào bản ghi đủ ngữ cảnh để kết luận thiếu một hành vi.
- Checkpoint, dữ liệu có quyền sử dụng, người chấm và quy trình giải quyết bất đồng.
- Ngưỡng chất lượng model, ngưỡng cần duyệt và phạm vi người có quyền xem/sửa hội thoại.

Những quyết định này chặn việc đóng băng nhãn và phát hành AI, không chặn xây dựng màn hình nhập/chấm thủ công với rubric bản nháp.
