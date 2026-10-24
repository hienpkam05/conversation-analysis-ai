# Hướng dẫn gán nhãn trạng thái

## Đơn vị và ý nghĩa

Một nhãn kết luận cho toàn bộ một revision của cuộc gọi. Nhãn mô tả trạng thái tương tác của ứng viên đối với cơ hội đang trao đổi ở cuối cuộc gọi, không đánh giá năng lực hoặc cơ hội trúng tuyển. Không suy từ tuổi, giới tính, quê quán, cảm xúc hay sự im lặng.

Đọc/nghe đầy đủ trước khi gán nhãn. Khi trạng thái thay đổi, chỉ chọn kết luận sau nếu có lời nói rõ ràng thay thế ý trước; giải thích diễn biến trong ghi chú. Nếu không chắc, chọn unknown, không lấy từ khóa cuối làm kết luận mặc định.

| Trạng thái | Chọn khi | Không suy thành |
| --- | --- | --- |
| Quan tâm | Ứng viên muốn tìm hiểu/ứng tuyển nhưng chưa nhận lời phỏng vấn | Đã có lịch hoặc đã nhận việc |
| Cần thêm thông tin | Còn câu hỏi/điều kiện chưa được giải quyết trước khi quyết định | Từ chối hoặc đồng ý ngay |
| Muốn liên hệ lại | Ứng viên đề nghị/đồng ý trao đổi lại vào dịp khác | Đồng ý tham gia phỏng vấn |
| Đồng ý phỏng vấn | Có lời đồng ý rõ, hoặc phản hồi rõ nghĩa trong đúng ngữ cảnh mời phỏng vấn | Chắc chắn đến, đã nhận việc hoặc đã có ngày giờ |
| Từ chối | Từ chối cơ hội đang trao đổi một cách rõ ràng | Cấm liên hệ vĩnh viễn, không phù hợp mọi công việc |
| Chưa đủ căn cứ | Thiếu ngữ cảnh, lời mâu thuẫn, không rõ ý, chưa nghe được kết luận | Một nhãn nghiệp vụ đoán cho đủ lớp |

“Vâng/dạ” đơn lẻ không đủ căn cứ; cần đối chiếu câu hỏi liền trước và diễn biến phía sau. Lời tư vấn viên “chị đồng ý rồi nhé” không thay được lời ứng viên. Không nhận lời phỏng vấn ở một công ty chưa chắc là từ chối mọi cơ hội; ghi rõ phạm vi nếu hội thoại có nhiều cơ hội.

## Quy trình trên web

1. Người phụ trách đăng nhập, mở Bộ nhãn và dữ liệu huấn luyện, đọc các định nghĩa và tài liệu này. Chỉ duyệt bộ nhãn khi đã thống nhất thật, ghi ghi chú. Không cần tạo nhãn giả để mở khóa.
2. Người gán nhãn kiểm tra audio/transcript, vai người nói và tình trạng audio usable ở tab đánh giá tư vấn. Nguồn thiếu/khó nghe cần sửa hoặc loại, không ép thành dữ liệu train.
3. Trong tab Trạng thái ứng viên, gán bản manual, chọn lời ứng viên làm căn cứ, ghi lý do và xác nhận. Có thể dùng quy tắc làm tham khảo, nhưng cần tự đối chiếu; không duyệt thẳng rules/model thành nhãn chuẩn.
4. Người phụ trách khác tác giả mở lại, nghe/đọc nguồn, ghi nhận định độc lập rồi Duyệt nhãn train hoặc Từ chối nhãn. Không tự duyệt nhãn mình đã tạo. Có thể dùng nguoi_cham_a/nguoi_cham_b gán và nguoi_duyet duyệt.
5. Nếu bị từ chối hoặc cần sửa, tạo bản manual mới có liên kết supersedes. Audit cũ giữ nguyên. Nếu có hai nhãn đã duyệt mâu thuẫn, xử lý bằng bản thay thế rõ ràng; exporter không tự quyết nhãn nào đúng.

## Kiểm tra trước khi xuất

- Đúng revision mới nhất, hash/định nghĩa không đổi, nguồn đã kiểm tra.
- Audio thật phải được đánh dấu usable. Việc xác nhận trạng thái không tự đánh dấu audio usable.
- Chỉ bản manual đã confirmed và được reviewer khác tác giả duyệt mới đủ điều kiện.
- Hội thoại mới cùng một người/chuỗi liên hệ phải có cùng mã nhóm; không dùng ID cuộc gọi làm nhóm riêng chỉ để có đủ số lượng.
- Xem phân bố từng lớp và báo cáo loại trừ. Chưa có đủ lớp thì thu thập thêm dữ liệu thật; không copy/sinh nhãn để qua kiểm tra.

Nhãn confirmed phục vụ nghiệp vụ chưa đồng nghĩa nhãn train đã duyệt độc lập. Nghiệm thu thật và phê duyệt bộ nhãn vẫn do người phụ trách thực hiện, không do script tự tạo.
