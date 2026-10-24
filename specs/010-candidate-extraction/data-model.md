# Dữ liệu 010

## CandidateProfile trong Django

UUID, revision FK PROTECT, revision_hash, utterances snapshot, fields JSON gồm đủ 10 mã trường, source rules/manual, status draft/confirmed, version, author, supersedes nullable, confirmed_by/at và created_at.

Mỗi trường: code, value (null/string/int), evidence (ID lượt + start/end Unicode code point + quote), options khi có nhiều khả năng, conflict và note. Chỉ candidate không unclear được chọn làm nguồn; không lấy tên/điện thoại tư vấn viên. Giá trị manual cần dẫn chứng nhưng vẫn cần người đối chiếu ý nghĩa, validator không chứng minh người dùng nhập đúng ngữ nghĩa.

Nội dung bản đã lưu bất biến. Muốn sửa tạo bản mới, không đổi bản quy tắc/gốc. Confirm cần manual, đúng optimistic version, nguồn mới nhất đã kiểm tra và không xung đột; revision được sealed. Nguồn thay đổi thì trạng thái cũ chỉ là lịch sử, không gửi tìm kiếm nữa.

## CampaignSearch trong Django

UUID, profile FK PROTECT, requested_by, query JSON tối thiểu, result JSON đã kiểm tra hợp đồng, created_at. Snapshot bất biến; không có selected_campaign hay thao tác tự gán. Không lưu kết quả thành công nếu HTTP/model/vector lỗi hoặc nguồn đã đổi lúc gọi mạng.

## PostgreSQL và Qdrant

Không thêm bảng hoặc sửa dữ liệu nghiệp vụ matching cho bản đầu. Đọc Campaign active/nondeleted, dùng ModelVersion active và EmbeddingRef đúng profile_hash/collection/model. Query vector chỉ trên ID đủ bộ lọc có ref hiện hành, kiểm lại payload và point ID khi nhận kết quả. Mỗi kết quả có model version và điểm cosine thô, không biểu diễn như độ chính xác tuyển dụng.

Trường ca/ngày bắt đầu chưa có cột tương ứng trong Campaign nên không có bảo đảm đáp ứng hai điều kiện này. Không lấy nơi ở ứng viên làm vùng muốn làm; vùng muốn làm do người dùng chọn có căn cứ.
