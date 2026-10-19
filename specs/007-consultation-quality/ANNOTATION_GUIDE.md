# Hướng dẫn chấm chất lượng tư vấn tuyển dụng

Ngày: 2026-10-19. Phiên bản: annotation-guide-2026-10-19, tương ứng quality-draft-v2.

Đây là bộ tiêu chí đề xuất để chấm thử và thống nhất nghiệp vụ, chưa được phê duyệt để tạo nhãn huấn luyện chính thức. Tất cả ví dụ bên dưới là tình huống giả định, không phải lời thoại hoặc điểm đã xác nhận của 20 audio mẫu. Định nghĩa trên web được trả từ `backend/consultation_quality/rubric.py`.

## 1. Chấm cái gì

Chấm hành vi tư vấn có thể kiểm tra từ nội dung hội thoại đã được nghe đối chiếu. Không chấm việc ứng viên có nhận việc hay không, không suy ra sự thật về công ty/lương khi không có dữ liệu đối chiếu, không đo âm điệu hoặc ngắt lời từ transcript.

Đơn vị chấm là một phiên bản hội thoại. Mỗi tiêu chí có một nhãn 0/1/2 hoặc Không đủ dữ liệu. Chấm riêng từng tiêu chí; một lời thoại có thể là bằng chứng cho nhiều tiêu chí nếu giải thích được hành vi liên quan. Không cho cả 5 mục cùng điểm chỉ vì có cảm giác chung tốt hoặc xấu.

## 2. Chuẩn bị trước khi chấm

1. Mở Đánh giá tư vấn và chọn Audio gán nhãn. Ghi mã cuộc gọi, mục đích chính, bản ghi có đủ đầu/cuối hay không.
2. Nghe cả cuộc gọi ít nhất một lượt. Nghe lại các đoạn đánh dấu nghi ngờ STT; các dấu hiệu đó không tự khẳng định đoạn nói sai.
3. Sửa lỗi transcript theo điều nghe được; không tự sửa lời của tư vấn viên thành câu hay hơn. Giữ nguyên phủ định, con số và điều kiện nếu nghe rõ; không đoán phần khó nghe.
4. Tách lượt theo người thực sự nói; gán Tư vấn viên/Ứng viên. Nếu vẫn không phân biệt được, giữ Chưa xác định và lưu nháp.
5. Xác nhận đã sửa transcript và kiểm tra vai trò, rồi Lưu hội thoại. Chỉ đánh dấu xác nhận khi đã thực hiện, không chỉ để qua validation.

Nếu audio hoàn toàn không có lời nói, nghe không rõ hoặc bị cắt, lưu Tình trạng bản ghi và lý do. Không bịa một lượt nói để tạo điểm. Nếu chỉ một phần không rõ, có thể ghi `[không nghe rõ]` tại phần đó và dùng Không đủ dữ liệu cho tiêu chí bị ảnh hưởng.

Các mẫu ngắn không đủ cơ hội tư vấn không phải mẫu tư vấn kém. Cuộc gọi chỉ xác nhận lịch hoặc trao đổi hành chính phải được ghi đúng mục đích; không ép phải lặp lại toàn bộ kịch bản tư vấn mới được điểm cao.

## 3. Chọn điểm 0 hay Không đủ dữ liệu

| Tình huống | Cách xử lý |
| --- | --- |
| Có đủ phần liên quan, có cơ hội thể hiện hành vi nhưng không thực hiện | 0, chọn bằng chứng thiếu hành vi hoặc lời thoại thể hiện lỗi |
| Hành vi xuất hiện nhưng còn thiếu nội dung đáng kể | 1, trích lượt nói thể hiện phần đã làm và nêu phần thiếu |
| Đạt đủ điều kiện mức 2 trong phạm vi cuộc trao đổi | 2, dẫn chứng rõ; không cần giống câu mẫu |
| Bị mất đầu/cuối, khó nghe, không kết nối được, không có cơ hội hoặc tiêu chí không áp dụng với mục đích cuộc gọi | Không đủ dữ liệu, ghi lý do cụ thể |
| Không chắc giữa hai mức do chưa hiểu quy tắc | Lưu nháp và ghi bất đồng để thảo luận; không chọn Không đủ dữ liệu chỉ để tránh quyết định |

Không gán 0 cho phần cuối chỉ vì bản ghi bị cắt trước khi chốt. Ngược lại, nếu nghe trọn phần kết thúc và thấy bỏ lửng hành động cần thiết, đó là điểm 0 chứ không phải thiếu dữ liệu.

## 4. Năm tiêu chí

### 4.1 Mở đầu và xác nhận mục đích

Kiểm tra ba nội dung: vai trò/đơn vị của người gọi, lý do trao đổi và xác nhận đúng người hoặc đúng ngữ cảnh.

| Nhãn | Quy tắc |
| --- | --- |
| 0 | Có đầu cuộc gọi đầy đủ nhưng không thể hiện nội dung nào trong ba nội dung cần kiểm tra; hoặc tiếp tục tư vấn dù biết nhầm người |
| 1 | Có một phần mở đầu nhưng còn thiếu một hoặc nhiều nội dung trên |
| 2 | Đủ ba nội dung bằng lời thoại hoặc ngữ cảnh được xác nhận trong bản ghi |
| Không đủ dữ liệu | Đầu bản ghi bị mất/khó nghe, không kết nối được với ứng viên |

Ví dụ 2: “Em là An bên tuyển dụng X. Chị có để lại nhu cầu tìm việc đúng không ạ?” — “Đúng rồi.” Ví dụ 1: “Alo, em gọi tuyển dụng đây” rồi vào tư vấn, không rõ đơn vị hoặc xác nhận ngữ cảnh. Một lời “alo/chào chị” đứng riêng chưa đạt 2. Không suy ra xác nhận danh tính từ tên file, số điện thoại hoặc hồ sơ ngoài cuộc gọi.

### 4.2 Khai thác nhu cầu

Nhóm nhu cầu: khu vực, loại việc/kỹ năng, thu nhập, ca làm, thời điểm bắt đầu và điều kiện hỗ trợ thiết yếu. Chỉ tính thông tin liên quan đến quyết định công việc.

| Nhãn | Quy tắc |
| --- | --- |
| 0 | Có cơ hội nhưng không làm rõ nhu cầu nào, hoặc bỏ qua ràng buộc ứng viên đã nêu rõ |
| 1 | Làm rõ một nhóm; hoặc có nhiều thông tin nhưng chưa xác nhận/sử dụng khi tư vấn |
| 2 | Làm rõ ít nhất hai nhóm liên quan, xác nhận hoặc sử dụng, không bỏ qua ràng buộc đã nêu |
| Không đủ dữ liệu | Ứng viên không tiếp tục, phần khai thác bị mất/khó nghe, hoặc cuộc gọi chỉ xác nhận hành chính |

Ví dụ 2: ứng viên tự nói muốn làm tại Bắc Ninh và chỉ làm ca ngày; tư vấn viên xác nhận sẽ tìm vị trí đáp ứng cả hai. Không bắt buộc hỏi lại khi ứng viên đã tự cung cấp. Hỏi “chị ở huyện nào” và “chị ở xã nào” chỉ làm rõ một nhóm khu vực. Không cộng điểm vì hỏi nhiều thông tin cá nhân không liên quan.

Ranh giới: hỏi đủ nhiều nhóm nhưng tiếp tục giới thiệu ca đêm dù ứng viên nói không thể đi ca đêm, không giải thích/không có sự đồng thuận đổi nhu cầu, thuộc mức 0 theo quy tắc bỏ qua ràng buộc; số câu hỏi không bù cho hành vi này.

### 4.3 Cung cấp thông tin công việc

Kiểm tra nội dung rõ ràng trong phạm vi tư vấn, không chứng thực thông tin đúng thực tế. Nhóm điều kiện gồm thu nhập, ca/giờ làm, yêu cầu công việc, hỗ trợ ăn ở/đi lại và chính sách liên quan.

| Nhãn | Quy tắc |
| --- | --- |
| 0 | Có cơ hội nhưng không cung cấp thông tin sử dụng được, hoặc né điều kiện cốt lõi ứng viên hỏi |
| 1 | Có thông tin cụ thể nhưng còn thiếu nội dung chính hoặc điều kiện còn mơ hồ |
| 2 | Rõ công việc và nơi làm, ít nhất hai nhóm điều kiện liên quan, giải thích các điều kiện ảnh hưởng đến đề nghị |
| Không đủ dữ liệu | Không có phần này trong bản ghi, mất phần tư vấn, hoặc cuộc gọi chỉ xác nhận lịch và không phát sinh nhu cầu giải thích công việc |

Ví dụ 2: nêu công việc lắp ráp tại khu vực X, ca làm và phân biệt lương cơ bản với phần tăng ca. Ví dụ 1: “Làm công nhân, thu nhập 10–14 triệu” nhưng không rõ công việc, nơi làm hoặc điều kiện để đạt khoản đó. Nhiều con số lương vẫn chỉ là một nhóm thông tin. Lương cao không làm tăng điểm và chưa có căn cứ để kết luận lương thật/giả.

### 4.4 Lắng nghe và giải đáp

Kiểm tra phản hồi theo điều ứng viên thực sự nói; sự tôn trọng chỉ chấm qua lời có trong hội thoại.

| Nhãn | Quy tắc |
| --- | --- |
| 0 | Có câu hỏi/băn khoăn rõ nhưng bỏ qua, lạc đề; hoặc có lời xúc phạm/ép buộc rõ ràng |
| 1 | Phản hồi có liên quan nhưng chỉ giải quyết một phần hoặc để câu hỏi quan trọng chưa rõ |
| 2 | Đáp đúng trọng tâm, làm rõ điều chưa hiểu; chưa biết thì nói rõ và thống nhất cách kiểm tra, giao tiếp tôn trọng |
| Không đủ dữ liệu | Không có trao đổi đủ nội dung để quan sát phản hồi, thiếu lượt một bên hoặc khó nghe phần liên quan |

Ví dụ 2: ứng viên hỏi xe đón, tư vấn viên nói chưa xác nhận tuyến và thống nhất sẽ kiểm tra theo khu vực rồi báo lại. Đây là cách phản hồi rõ ràng, không chứng minh có tuyến xe. Chỉ nói “vâng” hoặc dùng lời lịch sự không tự đạt 2. Không bắt buộc ứng viên phải phản đối mới chấm được: xác nhận và phản hồi nhu cầu họ nêu cũng là tương tác có thể quan sát.

### 4.5 Thống nhất bước tiếp theo

Chấm kết thúc phù hợp với ý định ứng viên. Không bắt buộc đặt lịch hoặc thuyết phục bằng được.

| Nhãn | Quy tắc |
| --- | --- |
| 0 | Có kết thúc đầy đủ nhưng bỏ lửng hành động cần thiết, hoặc phớt lờ yêu cầu dừng liên hệ |
| 1 | Có bước tiếp nhưng thiếu ai làm/gì/kênh hoặc thời gian cần thiết, hay thiếu phản hồi xác nhận |
| 2 | Hai bên xác nhận ai làm gì, kênh/thời gian khi cần; hoặc xác nhận tôn trọng quyết định không tiếp tục |
| Không đủ dữ liệu | Mất phần kết, ngắt đột ngột, khó nghe hoặc chưa có đối thoại đủ để thống nhất |

Ví dụ 2: “Em gửi địa chỉ qua Zalo số đang gọi sau cuộc gọi nhé?” — “Vâng.” Ví dụ 1: “Em gửi sau nhé” rồi kết thúc, chưa rõ kênh hoặc xác nhận. Trường hợp ứng viên nói không có nhu cầu và xin ngừng liên hệ, tư vấn viên ghi nhận và kết thúc phù hợp cũng đạt 2; không hạ điểm vì không tuyển được người.

## 5. Chọn dẫn chứng trên web

Chọn radio tiêu chí đang chấm rồi tích Dẫn chứng ở các lượt nói liên quan. Với điểm 1/2 cần ít nhất một lượt của tư vấn viên; thêm lượt ứng viên chứa câu hỏi/ràng buộc để người khác hiểu ngữ cảnh.

Điểm 0 vì hành vi không xuất hiện: chọn loại Hành vi không xuất hiện, chọn phạm vi lời thoại đã nghe và ghi phần còn thiếu. Với phần mở đầu, phạm vi thường là các lượt đầu đủ ngữ cảnh; với hành vi bỏ qua một nhu cầu, kèm lượt nêu nhu cầu và phần tư vấn tiếp. Không trích một câu giả làm bằng chứng cho sự vắng mặt.

Nếu lời thoại thể hiện lỗi cụ thể, như trả lời lạc đề, có thể dùng loại Lời thoại cho điểm 0 và chọn cả câu hỏi lẫn câu trả lời. Không đủ dữ liệu cần lý do cụ thể, ví dụ “mất phần kết sau giây 35”, không chỉ ghi “không biết”.

Lưu nháp cho phép làm dở. Hoàn tất · Chờ duyệt yêu cầu xác nhận transcript/người nói và đủ lý do/dẫn chứng. Hệ thống chưa có bước duyệt chính thức; trạng thái chờ duyệt không đồng nghĩa đủ điều kiện train.

## 6. Điểm tổng

Mỗi tiêu chí có trọng số đề xuất 20%. Khi đủ 5 điểm và dẫn chứng hợp lệ, tổng = 10 × tổng điểm năm tiêu chí, từ 0 đến 100. Có một mục Không đủ dữ liệu hoặc dẫn chứng nháp chưa hợp lệ thì tổng để trống, không chuyển nhãn thiếu thành 0 và không chia lại trọng số.

Ví dụ giả định: [2, 1, 2, 1, 2] → 80/100. [2, 1, Không đủ dữ liệu, 1, 2] → không có điểm tổng. Không đặt ngưỡng tốt/kém hoặc dùng tổng để quyết định nhân sự trong đợt pilot.

## 7. Chấm thử và xử lý bất đồng

Bắt đầu với call_0387, call_0994 và call_1066 trong 20 mẫu đã đăng ký. Đây chỉ là lựa chọn thử theo thời lượng vừa phải, chưa phân loại tốt/xấu. Dùng [PILOT_REVIEW.md](PILOT_REVIEW.md) ghi kết quả.

Nếu có hai người chấm, cả hai dùng cùng revision transcript đã sửa và cùng quality-draft-v2. Người A/B chấm độc lập trước khi xem điểm của nhau; ghi mã bản chấm và mã transcript hiển thị trong lịch sử. Ứng dụng local hiện chưa quản lý danh tính người chấm nên mã A/B được ghi trong phiếu, không mặc định mỗi bản lưu là một người độc lập.

Thảo luận từng bất đồng: lỗi nghe/role, thiếu ngữ cảnh, hiểu khác mức điểm hay khác phạm vi áp dụng. Ghi quyết định và lý do; nếu sửa transcript, hai người chấm lại trên cùng revision mới. Không lấy trung bình hai nhãn 0 và 2 để tự tạo nhãn 1.

Với 3 cuộc và 5 tiêu chí có 15 cặp quyết định: có thể báo số cặp trùng nhau và loại bất đồng, nhưng không xem đó là chứng minh rubric/model đáng tin cậy. Chưa có model nên không có F1 để báo. Sau khi sửa hướng dẫn, chấm lại pilot trước khi mở rộng 20 cuộc.

## 8. Cổng trước khi tạo nhãn chuẩn

- Người phụ trách duyệt phạm vi cuộc gọi áp dụng, năm tiêu chí, các ranh giới và trọng số.
- Có transcript/role đã được người nghe kiểm tra, dẫn chứng đúng revision và người chấm được ghi nhận.
- Đã giải quyết bất đồng pilot và thống nhất quy tắc cho cuộc ngắn, cuộc từ chối, cuộc theo dõi và bản ghi bị cắt.
- Ghi người duyệt, ngày duyệt và phiên bản; cập nhật trạng thái rubric bằng một bước triển khai có kiểm tra. Tài liệu này không tự duyệt thay người phụ trách.

Việc huấn luyện và xuất tập nhãn được phép train vẫn chưa thực hiện. Không đổi trạng thái nhãn chỉ bằng cách ghi “đã duyệt” trong nhận xét.
