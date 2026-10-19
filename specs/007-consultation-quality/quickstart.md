# Hướng dẫn kiểm thử 007

Trạng thái: đã có đăng nhập, phân quyền, sửa/khóa transcript, chấm độc lập, quản lý và duyệt rubric, biên bản pilot và duyệt nhãn. Chưa có nhãn thật được duyệt hoặc model chất lượng. Xem implementation.md và biên bản A/B ngày 2026-10-19.

## Tạo tài khoản một lần

Từ D:\NCKH, chạy từng lệnh; mỗi tài khoản mới sẽ yêu cầu nhập mật khẩu ẩn ít nhất 12 ký tự, nhập lại để xác nhận. Không có mật khẩu mặc định:

```powershell
venv\Scripts\python.exe -X utf8 backend\manage.py migrate
venv\Scripts\python.exe -X utf8 backend\manage.py quality_user nguoi_duyet --reviewer --assign-pilot
venv\Scripts\python.exe -X utf8 backend\manage.py quality_user nguoi_cham_a --assign-pilot
venv\Scripts\python.exe -X utf8 backend\manage.py quality_user nguoi_cham_b --assign-pilot
```

Đây phải là ba người khác nhau khi nghiệm thu chấm kép thật, không phải một người đăng nhập ba tên để tạo nhãn độc lập giả. `--assign-pilot` giao các hội thoại audio đã đăng ký cho tài khoản. Nếu đăng ký thêm mẫu sau đó, chạy lại lệnh không cần đặt lại mật khẩu. Thêm `--reset-password` khi cần đổi mật khẩu. Người duyệt không mặc nhiên là Django admin/superuser.

## Chạy màn gán nhãn

1. Dùng database Django đã cấu hình và môi trường Python của dự án; chạy migration và server:

```powershell
cd backend
..\venv\Scripts\python.exe manage.py migrate
..\venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

2. Mở terminal mới tại gốc dự án để chạy Vue:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

3. Mở URL Vite in ra; chọn tab Đánh giá tư vấn, đăng nhập và chọn mẫu trong Audio gán nhãn. Mẫu chưa nhận dạng xong bị vô hiệu hóa. Có thể bấm Cập nhật danh sách.
4. Nghe audio, sửa nội dung, gán vai trò. Nếu một segment có nhiều người nói, xuống dòng tại ranh giới rồi bấm Tách lượt. Không tự gán vai xen kẽ.
5. Xác nhận đã kiểm tra vai trò và đã nghe đối chiếu/sửa transcript, rồi Lưu hội thoại.
6. Chọn tiêu chí bằng radio, chọn Dẫn chứng ở các lượt bên trái, chấm điểm và ghi nhận xét. Có thể Lưu nháp khi đang làm dở. Hoàn tất · Chờ duyệt chỉ thành công khi đáp ứng điều kiện; không làm nhãn thành dữ liệu đã duyệt.
7. Một tiêu chí Không đủ dữ liệu cần lý do khi hoàn tất; tổng điểm để trống. Hành vi không xuất hiện cần điểm 0, phạm vi lời thoại đã xem và lời giải thích.
8. Mở lại từ danh sách; sửa hội thoại lưu thành revision mới. Chọn Phiên bản transcript để xem lại điểm và dẫn chứng trên bản cũ.

Mở Quy tắc chấm ở đầu màn hình và Mức điểm và ví dụ trong từng tiêu chí để tra quality-draft-v2. Đọc ANNOTATION_GUIDE.md và dùng PILOT_REVIEW.md để chấm thử call_0387, call_0994, call_1066. Đây chưa phải ba mẫu đã có nhãn. Lịch sử hiển thị mã bản chấm và transcript để ghi vào phiếu. Nếu bản cũ dùng v1, điểm cũ không được tự điền sang v2; bản gốc vẫn được giữ trong lịch sử.

Với mẫu không có lời nói hoặc khó nghe, chọn Tình trạng bản ghi và ghi chú, bấm Lưu tình trạng bản ghi. Không cần bịa lượt nói để có điểm. Đây là đánh giá khả năng dùng audio, không phải điểm chất lượng tư vấn hoặc phê duyệt dữ liệu huấn luyện.

## Chốt nghiệp vụ A trên web

1. Người phụ trách mở Quản lý bộ tiêu chí, kiểm tra định nghĩa và trọng số. Sửa nháp chỉ khi chưa có ai dùng để chấm; nếu đã dùng thì Tạo phiên bản mới. Chọn cùng phiên bản trên tất cả tài khoản.
2. Người chấm A nghe/sửa ba mẫu đề xuất call_0387, call_0994, call_1066, xác nhận vai trò và transcript, lưu hội thoại; lưu tình trạng Có thể chấm hoặc Bản ghi bị cắt có ghi chú. Người chấm B nghe đối chiếu cùng revision; nếu phải sửa nữa, hai người cùng chấm lại trên revision mới nhất.
3. A và B tự chấm rồi Hoàn tất · Chờ duyệt. Người chấm thường không xem được điểm của người kia; không thay đổi transcript sau khi bắt đầu chấm nếu muốn đối chiếu cùng revision.
4. Người duyệt đăng nhập, mở mẫu và mục Chấm kép và giải quyết bất đồng. Chọn đúng hai bản chấm; đối chiếu bảng từng tiêu chí và dẫn chứng trong lịch sử. Điền điểm, dẫn chứng và nhận xét kết luận ở form chấm, lưu bản chấm của người duyệt trên cùng revision. Ghi lý do thống nhất, bấm Lập biên bản theo điểm và dẫn chứng đang chọn. Không lấy trung bình 0/2 thành 1 một cách máy móc.
5. Lặp lại trên ba cuộc gọi khác nhau. Mở Chốt rubric, xác nhận tiêu chí/mức điểm/trọng số, ghi kết luận và Duyệt bộ tiêu chí. Server chặn nếu mới có 0/1/2 cuộc hoặc người phân xử trùng người chấm.
6. Sau khi rubric đã duyệt, mở Duyệt bản chấm, ghi nhận xét và duyệt bản kết luận phù hợp. Duyệt rubric không tự duyệt nhãn. Chưa có lệnh train nào được chạy.

Nếu cần đổi định nghĩa sau pilot, tạo rubric mới và chấm lại theo phiên bản đó; không chuyển điểm cũ sang phiên bản mới tự động. Hai tài khoản dùng các phiên trình duyệt khác nhau hoặc đăng xuất/đăng nhập lần lượt; đăng xuất chỉ sau khi đã lưu.

## Kiểm tra storage và code

```powershell
venv\Scripts\python.exe -X utf8 backend\manage.py check_quality_storage
venv\Scripts\python.exe -X utf8 backend\manage.py test consultation_quality
```

Storage command tạo bản ghi thăm dò rồi rollback, không thêm nhãn. Dữ liệu quality lưu trong SQLite Django, PostgreSQL ở matching_service không bị đổi. Bản sao trước migration đợt A/B nằm tại data/quality_dataset/backups/, được Git ignore. Máy clone mới không có audio/database local; cần tự nhập dữ liệu và tạo tài khoản.

## Chuẩn bị 20 mẫu bằng model local

Từ thư mục gốc, sau migration:

```powershell
venv\Scripts\python.exe -u backend\manage.py prepare_quality_pilot data/quality_dataset/pilot.json --model-path "DUONG_DAN_CHECKPOINT_LOCAL" --threads 8 --batch-size 4
```

Checkpoint là thư mục có `model.bin`, config và tokenizer của faster-whisper. Command chỉ dùng checkpoint local, không tải model hoặc đưa audio ra ngoài. Mặc định không chỉ định batch-size sẽ dùng suy luận từng đoạn. Các mẫu đã ready/no_speech được bỏ qua khi chạy lại; các mẫu failed/running do ngắt được thử lại. Không chạy hai lệnh batch cùng lúc trên cùng manifest.

`--register-only` chỉ đăng ký danh sách để nghe, chưa tạo transcript. Mẫu không có lời nói được đánh dấu no_speech với revision rỗng; người chấm vẫn nghe và có thể thêm lời thủ công, không có điểm được tự sinh.

Xuất transcript hiện có để đối chiếu ngoài web:

```powershell
venv\Scripts\python.exe backend\manage.py export_quality_transcripts data/quality_dataset/review-transcripts.json
```

File JSON có purpose=human_review_only, không xuất điểm chấm thành nhãn train. Khi đợt STT chưa xong, các mẫu pending/running chưa có đầy đủ lời thoại; chạy lại lệnh sau khi nhận dạng hoàn tất để cập nhật. review_flags chỉ là dấu hiệu cần nghe, không phải kết luận nội dung sai. Tình trạng bản ghi và phê duyệt nhãn là hai việc khác nhau.

Nếu cổng Django phải đổi, chỉnh proxy `/api` trong `frontend/vite.config.js` tương ứng rồi restart Vite. Chức năng quality dự kiến đi qua Django; API matching ở 8001 không cung cấp endpoint này.

## D/E: Thực nghiệm và AI còn chờ

Phần chuẩn bị dữ liệu D đã có lệnh kiểm tra/xuất/chia tập/baseline tại [TRAINING.md](TRAINING.md). Fine-tune, báo cáo thật và ngưỡng phát hành vẫn chưa hoàn thành. Chỉ chạy khi có nhãn approved và đã kiểm tra riêng tư/nhóm, không dùng transcript nháp làm nhãn.

Phần tích hợp E hiện đã có hàng đợi/worker/API và khung Chấm AI; xem [AI_RUNTIME.md](AI_RUNTIME.md). Thiếu checkpoint thì nút bị khóa và API không tạo job/điểm giả. Sau khi D có model đúng định dạng đã được duyệt, dùng cùng QUALITY_MODEL_DIR ở Django và worker, chạy `venv\Scripts\python.exe -X utf8 backend\manage.py run_quality_worker` trong terminal riêng. Việc đã có khung AI không thay thế fine-tune hoặc nghiệm thu model.

- Chuẩn bị checkpoint đã fine-tune và cấu hình inference theo hướng dẫn sẽ viết khi triển khai; chưa có lệnh huấn luyện/cấu hình model chính thức ở thời điểm tạo spec.
- Kiểm tra model-status; thử job với model thiếu phải báo rõ, không tạo điểm.
- Chạy một hội thoại đã xác nhận vai trò, theo dõi trạng thái job rồi đối chiếu điểm và dẫn chứng với người chấm.
- Thử transcript dài có hành vi chốt ở phần cuối để kiểm tra không bị cắt mất.

## Ghi kết quả

Ghi commit, cấu hình, phiên bản rubric/model, dữ liệu thử đã ẩn danh, lệnh, kết quả và lỗi thực tế vào biên bản chạy. Không ghi nội dung hội thoại thật hoặc thông tin liên hệ trong tài liệu công khai.
