# Spec 010: Thông tin ứng viên và gợi ý chiến dịch

## Luồng

Transcript đã lưu → bản trích xuất có câu nguồn → người dùng sửa/xác nhận → gửi thông tin nghề nghiệp tối thiểu tới Matching Service → xem chiến dịch đang hoạt động được xếp hạng bằng embedding hiện có.

## Phạm vi bản đầu

- Họ tên, số điện thoại, nơi ở hiện tại, nơi muốn làm, vùng muốn làm, công việc, kinh nghiệm, ca làm, lương mong muốn VND/tháng và thời điểm có thể đi làm.
- Quy tắc chỉ lấy thông tin từ lời ứng viên nghe rõ với dấu hiệu tường minh. Không dùng lời giới thiệu lương/công ty của tư vấn viên làm mong muốn ứng viên. Nơi ở không tự biến thành nơi muốn làm.
- Mỗi trường có value, evidence (ID lượt, start/end theo Unicode code point, quote nguyên văn), options và conflict. Có nhiều giá trị khác nhau thì không tự chọn giá trị cuối.
- Sửa bằng bản manual riêng, giữ snapshot/hash nguồn và lịch sử. Trường thiếu để null, không ép đủ hồ sơ. Trường có giá trị phải có dẫn chứng ứng viên nghe rõ.
- Xác nhận cần transcript/vai đã kiểm tra, revision hiện hành, đúng version và không còn trường xung đột. Khóa nguồn sau xác nhận.
- Tìm chiến dịch chỉ khi bản manual đã xác nhận và người dùng đồng ý gửi thông tin nghề nghiệp. Không gửi họ tên, số điện thoại, nơi ở hoặc toàn transcript. Chưa tạo/cập nhật Candidate PostgreSQL hoặc gán chiến dịch tự động.
- Bổ sung POST /api/v1/campaigns/search: đọc chiến dịch active/nondeleted, lọc vùng (nếu yêu cầu) và lương tối thiểu (chỉ khi chọn lọc cứng), kiểm vector đúng phiên bản/profile hiện tại và tìm bằng Qdrant. Điểm cosine là độ tương đồng, không phải xác suất được tuyển.
- Ca làm và ngày bắt đầu chưa có cột có cấu trúc trong Campaign: hiển thị cần đối chiếu, không khẳng định đã thỏa điều kiện.

## Mô hình và giới hạn

NER hiện là quy tắc minh bạch, chưa có PhoBERT NER đã fine-tune. Semantic search dùng provider embedding của matching hiện có, không dùng model giả khi thiếu dependency/model/vector. Huấn luyện NER cần bộ nhãn span/BIO được duyệt, ngoài bản đầu này. Chưa nghiệm thu độ chính xác trích xuất trên audio thật.

## Nghiệm thu

1. Có tab xem/sửa thông tin, nguồn từng trường, lịch sử và trạng thái stale.
2. Không lấy thông tin của tư vấn viên; không tự chuyển nơi ở thành nơi muốn làm hay ngày tương đối thành ngày cụ thể.
3. Bản xung đột/chưa kiểm tra/cũ không thể xác nhận hoặc gửi tìm kiếm.
4. Lưu kết quả tìm kiếm và query tối thiểu để đối chiếu, không gán chiến dịch tự động.
5. Matching down/timeout/HTML/lỗi vector trả lỗi rõ, không báo thành công rỗng giả.
