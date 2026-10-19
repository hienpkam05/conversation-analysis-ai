"""Frozen quality-draft-v2 seed for migration 0005. Do not edit."""

RUBRIC = {
    "version": "quality-draft-v2",
    "status": "draft",
    "guidance_version": "annotation-guide-2026-10-19",
    "general_rules": [
        "Chấm hành vi có trong hội thoại đã nghe đối chiếu, không chấm việc ứng viên có nhận việc hay không.",
        "Không đủ ngữ cảnh, khó nghe hoặc không có cơ hội đánh giá: chọn Không đủ dữ liệu và ghi lý do; không tự chấm 0.",
        "Điểm 1/2 cần lời của tư vấn viên và ngữ cảnh liên quan. Điểm 0 do thiếu hành vi dùng phạm vi đã xem và giải thích.",
        "Ví dụ là tình huống giả định để thống nhất cách chấm, không phải nhãn của các audio mẫu.",
    ],
    "criteria": [
        {
            "code": "opening", "name": "Mở đầu và xác nhận mục đích", "weight": 0.2,
            "description": "Kiểm tra giới thiệu vai trò/đơn vị, nêu lý do gọi và xác nhận đúng người hoặc đúng ngữ cảnh trao đổi.",
            "levels": {
                "0": "Có phần đầu đầy đủ nhưng không thể hiện nội dung nào trong ba nội dung mở đầu cần kiểm tra; hoặc tiếp tục tư vấn dù biết đang nhầm người.",
                "1": "Có ít nhất một nội dung mở đầu nhưng còn thiếu vai trò/đơn vị, mục đích hoặc xác nhận người/ngữ cảnh.",
                "2": "Có đủ vai trò/đơn vị, mục đích và xác nhận người/ngữ cảnh bằng lời thoại; không bắt buộc theo một câu mẫu.",
            },
            "not_assessable": "Thiếu đầu cuộc gọi, không nghe rõ phần đầu hoặc không kết nối được với ứng viên.",
            "boundary": "Có lời chào chưa đủ điểm 2. Người chấm không tự suy ra người nhận đã được xác nhận từ tên file hay số điện thoại.",
            "example": "Tư vấn: Em là An bên tuyển dụng X. Chị có để lại nhu cầu tìm việc đúng không ạ? Ứng viên: Đúng rồi. → 2 nếu đoạn mở đầu đầy đủ.",
        },
        {
            "code": "needs", "name": "Khai thác nhu cầu", "weight": 0.2,
            "description": "Làm rõ nhu cầu liên quan và dùng thông tin đó khi tư vấn. Nhóm nhu cầu: khu vực, loại việc/kỹ năng, thu nhập, ca làm, thời điểm bắt đầu, điều kiện hỗ trợ thiết yếu.",
            "levels": {
                "0": "Có cơ hội trao đổi nhưng không làm rõ nhu cầu nào; hoặc bỏ qua ràng buộc ứng viên đã nêu rõ.",
                "1": "Làm rõ một nhóm nhu cầu; hoặc có nhiều thông tin nhưng chưa xác nhận hay sử dụng để tư vấn phù hợp.",
                "2": "Làm rõ ít nhất hai nhóm nhu cầu liên quan, xác nhận hoặc sử dụng chúng để tư vấn; không bỏ qua ràng buộc đã nêu.",
            },
            "not_assessable": "Ứng viên không tiếp tục trao đổi, phần khai thác bị mất/khó nghe, hoặc đây chỉ là cuộc xác nhận hành chính không có nhu cầu cần làm rõ.",
            "boundary": "Ứng viên tự nói nhu cầu vẫn được tính khi tư vấn viên xác nhận hoặc sử dụng. Hai câu cùng hỏi khu vực chỉ là một nhóm; không hỏi thêm dữ liệu cá nhân để kiếm điểm.",
            "example": "Ứng viên: Chị muốn ở Bắc Ninh, chỉ làm ca ngày. Tư vấn: Vậy em tìm vị trí ca ngày tại Bắc Ninh cho chị. → 2 nếu không bỏ qua ràng buộc khác đã nêu.",
        },
        {
            "code": "job_information", "name": "Cung cấp thông tin công việc", "weight": 0.2,
            "description": "Đánh giá mức rõ ràng và đầy đủ trong phạm vi cuộc tư vấn; không xác minh lương hay điều kiện có đúng thực tế khi thiếu nguồn đối chiếu.",
            "levels": {
                "0": "Có cơ hội tư vấn công việc nhưng không có thông tin sử dụng được; hoặc né tránh điều kiện cốt lõi ứng viên hỏi.",
                "1": "Có thông tin công việc cụ thể nhưng còn thiếu nội dung chính hoặc các điều kiện liên quan còn mơ hồ.",
                "2": "Nêu rõ công việc và nơi làm, ít nhất hai nhóm điều kiện liên quan; giải thích được điều kiện ảnh hưởng đến đề nghị như lương cơ bản so với thu nhập có tăng ca.",
            },
            "not_assessable": "Không có phần tư vấn công việc trong bản ghi, bị cắt trước phần này, hoặc chỉ xác nhận lịch đã thống nhất và không phát sinh yêu cầu giải thích công việc.",
            "boundary": "Nhóm điều kiện gồm thu nhập, ca/giờ làm, yêu cầu công việc, hỗ trợ ăn ở/đi lại và chính sách liên quan. Nhiều con số lương vẫn là một nhóm. Không tự cho điểm cao vì mức lương cao.",
            "example": "Tư vấn nêu vị trí lắp ráp tại khu vực X, ca làm, lương cơ bản và phần tăng ca tách biệt. → 2 nếu rõ ràng và đáp ứng nội dung được hỏi; chưa chứng minh thông tin đúng thực tế.",
        },
        {
            "code": "interaction", "name": "Lắng nghe và giải đáp", "weight": 0.2,
            "description": "Đánh giá phản hồi theo nội dung ứng viên nói và sự tôn trọng thể hiện bằng lời; không suy đoán cảm xúc hay ngắt lời từ transcript.",
            "levels": {
                "0": "Có câu hỏi/băn khoăn rõ nhưng tư vấn viên bỏ qua, trả lời lạc đề; hoặc dùng lời xúc phạm/ép buộc rõ ràng.",
                "1": "Có phản hồi liên quan nhưng mới giải quyết một phần hoặc vẫn để câu hỏi quan trọng không được làm rõ.",
                "2": "Phản hồi đúng trọng tâm các vấn đề đã nêu, làm rõ điều chưa hiểu; nếu chưa biết thì nói rõ và thống nhất cách kiểm tra lại, giao tiếp tôn trọng.",
            },
            "not_assessable": "Không có trao đổi đủ nội dung để quan sát phản hồi, mất lượt của một bên hoặc đoạn liên quan không nghe rõ.",
            "boundary": "Không bắt buộc ứng viên phải phản đối mới chấm được. Chỉ nói vâng/lịch sự không tự đạt 2; thừa nhận chưa biết và có cách kiểm tra không mặc nhiên là điểm kém.",
            "example": "Ứng viên hỏi có xe đón không; tư vấn viên nói rõ chưa xác nhận tuyến, sẽ kiểm tra tuyến theo khu vực và báo lại qua kênh hai bên thống nhất. → 2 cho cách phản hồi, không phải xác minh có xe.",
        },
        {
            "code": "next_steps", "name": "Thống nhất bước tiếp theo", "weight": 0.2,
            "description": "Kiểm tra kết thúc có hành động phù hợp với ý định ứng viên, hoặc xác nhận dừng liên hệ khi ứng viên từ chối.",
            "levels": {
                "0": "Bản ghi có kết thúc đầy đủ nhưng bỏ lửng khi cần hành động tiếp; hoặc phớt lờ yêu cầu dừng liên hệ rõ ràng.",
                "1": "Có đề xuất bước tiếp nhưng còn mơ hồ ai làm, làm gì, kênh liên hệ hoặc thời gian cần thiết; chưa có phản hồi xác nhận của ứng viên.",
                "2": "Hai bên xác nhận ai làm gì và kênh/thời gian khi cần; hoặc xác nhận tôn trọng việc ứng viên không tiếp tục và kết thúc phù hợp.",
            },
            "not_assessable": "Không có phần kết thúc do bản ghi bị cắt/ngắt đột ngột, không nghe rõ hoặc chưa có đối thoại đủ để thống nhất bước tiếp.",
            "boundary": "Không bắt buộc đặt lịch phỏng vấn. Ứng viên từ chối không làm giảm điểm nếu tư vấn viên ghi nhận và kết thúc phù hợp.",
            "example": "Tư vấn: Em gửi địa chỉ qua Zalo số đang gọi sau cuộc gọi nhé? Ứng viên: Vâng. → 2. Chỉ nói em gửi sau nhé, thiếu kênh và xác nhận → 1 nếu kết thúc đầy đủ.",
        },
    ],
}
