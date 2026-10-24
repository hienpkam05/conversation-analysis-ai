# Spec 009: Phân loại trạng thái ứng viên

## Mục tiêu và phạm vi

Từ một phiên bản hội thoại đã lưu, đề xuất trạng thái tương tác của ứng viên và lời nói làm căn cứ. Người dùng nghe/đọc lại, sửa và xác nhận. Không chấm khả năng làm việc, không tự loại ứng viên, không tạo lịch hay đổi dữ liệu matching.

Đây là bộ nhãn **đề xuất cần nghiệm thu**, không phải bảng trạng thái đã trích từ tài liệu gốc. File Word hiện có chỉ mô tả matching; ảnh đề cương nói 5 trạng thái nhưng không cung cấp định nghĩa đầy đủ.

| Mã | Ý nghĩa | Ví dụ lời ứng viên |
| --- | --- | --- |
| interested | Quan tâm, chưa chốt phỏng vấn | Tôi quan tâm công việc này. |
| needs_information | Cần thêm thông tin | Cho chị hỏi mức lương thế nào? |
| callback_requested | Muốn liên hệ lại, chưa đồng nghĩa nhận lời phỏng vấn | Em gọi lại cho chị sau nhé. |
| interview_agreed | Đồng ý tham gia phỏng vấn, không đồng nghĩa đã có lịch cụ thể | Tôi đồng ý phỏng vấn. |
| declined | Từ chối cơ hội đang trao đổi | Chị không có nhu cầu nữa. |
| unknown | Chưa đủ căn cứ, ngoài 5 nhãn nghiệp vụ | Vâng, dạ, lời tư vấn viên, lời mâu thuẫn hoặc thiếu nguồn. |

## Nguyên tắc

- Chỉ lời ứng viên rõ vai, không đánh dấu khó nghe, mới làm căn cứ cho gợi ý.
- V1 dùng quy tắc bảo thủ, trả source=rules, confidence=null. Không phải ViDeBERTa và không hiển thị phần trăm độ chính xác giả.
- Không diễn giải “vâng”, im lặng, lời hứa của tư vấn viên hay câu phủ định thành sự đồng ý. Có nhiều trạng thái được phát hiện thì trả unknown để người dùng đối chiếu.
- Ghi snapshot transcript, hash, phiên bản nhãn, người tạo và thời gian. Bản sửa là bản mới, giữ nguyên bản gợi ý gốc.
- Xác nhận cần transcript/vai đã kiểm tra, là revision mới nhất và hash/snapshot không đổi; có lời ứng viên làm căn cứ hoặc lý do chưa đủ căn cứ. Khóa revision khi xác nhận.
- Chỉ tác giả hoặc người có quyền duyệt được xác nhận. Hội thoại dùng quyền truy cập của Spec 007.
- Ghi nhận thủ công không mặc nhiên là nhãn chuẩn để train. Chưa train, chưa đo độ chính xác, chưa phát hành ViDeBERTa.

## Nghiệm thu bản đầu

1. Chọn hội thoại/revision, nghe nguồn, xem từng lượt và gợi ý có dẫn chứng.
2. Tạo nhãn thủ công, chọn trạng thái/lời dẫn chứng/ghi chú và lưu bản mới.
3. Xác nhận rõ ràng; không xác nhận nguồn cũ, chưa kiểm tra hoặc không có căn cứ hợp lệ.
4. Xem lại lịch sử và trạng thái đã xác nhận hiện hành; bản mới dạng nháp không thay trạng thái đã xác nhận.
5. Mâu thuẫn, phủ định, lời tư vấn viên, “vâng” đơn lẻ đều không trở thành đồng ý phỏng vấn.
6. Không ghi nhãn vào dữ liệu matching, tạo lịch hoặc gửi thông báo.
