# Kết quả chạy Spec 010 ngày 23/10/2026

## Triển khai và giữ dữ liệu

- Đã backup SQLite trước migration tại data/quality_dataset/backups/before-candidate-info-2026-10-23.sqlite3.
- Đã áp dụng candidate_info.0001_initial, chỉ thêm schema, không gán thông tin cho hội thoại thật.
- Sau kiểm thử database Django thật vẫn có 20 audio, 20 revision và ba tài khoản nguoi_duyet/nguoi_cham_a/nguoi_cham_b; 0 CandidateProfile và 0 CampaignSearch. Không tạo nhãn trạng thái/phê duyệt taxonomy hộ người dùng.
- Sửa .gitignore từ models/ sang /models/ để chỉ bỏ cache trọng số ở gốc, không bỏ nhầm mã nguồn matching_service/app/db/models có sẵn. Các file ORM không bị sửa hoặc xóa.
- Dependency kiểm thử matching được cài vào .cache/spec010-test-deps riêng, không thay dependency môi trường web. Do ACL môi trường sandbox, pytest matching được chạy với quyền truy cập phù hợp thư mục này.

## Kiểm thử tự động

- Django toàn bộ consultation_quality/conversation_followup/candidate_status/candidate_info: **141 tests đạt** ở lượt chạy cuối.
- Matching pytest, bỏ backend trio tùy chọn: 25 passed, 1 skipped. Test ghi/xóa Qdrant integration bỏ qua vì không có TEST_QDRANT_URL riêng; không dùng collection nghiệp vụ cho test ghi/xóa. Có cảnh báo deprecation Starlette/httpx từ dependency test, không lỗi test.
- Build frontend đạt; makemigrations --check không thiếu migration; diff --check không lỗi whitespace, chỉ cảnh báo CRLF.
- Kiểm tra nguồn riêng từng trường, vị trí nguyên văn, emoji/code point, mâu thuẫn/overflow, phủ định, thiếu đơn vị lương, nơi ở/nơi muốn làm, quyền/CSRF/stale/version, query tối thiểu, timeout và response guards.

## HTTP mô phỏng và trình duyệt

- Postman CLI 1.73.0, simulation candidate-info-contract tại localhost:4930/matching, không ghi lịch sử cloud. Fixture công khai trong postman/mocks và simulation trong postman/simulations.
- Database kiểm thử tách biệt .cache/spec010-browser.sqlite3, Django test 8004; không dùng database thật để xác nhận/gán fixture.
- Playwright/Edge desktop 1440x1000 và mobile 390x844: trích xuất, sửa vùng/dẫn chứng, lưu, xác nhận, đồng ý gửi, tìm kiếm, mở lại lịch sử và đăng xuất đều đạt.
- Đã kiểm log simulation: query thực do python-requests gửi chỉ gồm job/experience/desired_location/region/shift/salary/top_k/strict_salary, không có tên/phone/nơi ở/full transcript của fixture.
- Khi upstream trả 503 hoặc HTML thay JSON: Django báo lỗi, không tăng số CampaignSearch và không hiển thị kết quả thành công giả. Timeout được kiểm bằng unit test; chưa chạy một yêu cầu HTTP treo đủ 30 giây trong browser test.
- Mobile viewport=390, body.scrollWidth=390; không có lỗi JavaScript. Đã xem ảnh fields/results/mobile, các artifact ở data/quality_dataset/info-* và được Git bỏ qua.

## Runtime thật

- Đã khởi động Docker matching_service-postgres-1/qdrant-1/api-1 với volume có sẵn, không seed/rebuild dữ liệu nghiệp vụ. Không dừng container dự án khác.
- Tận dụng image matching local đã có dependency: tạo lớp COPY app cho code mới bằng Dockerfile helper trong .cache. Không tải lại/cài lại PyTorch vào image. Lần clone/build bình thường vẫn dùng Dockerfile dự án.
- Health HTTP 200: postgres=ok, qdrant=ok. Dữ liệu có sẵn: 5 campaigns, 10 embedding_refs, active model vinai/phobert-base-v2 / meanpool-v1, model_version_id 6090b3f2-3095-5bf9-8116-aeac638367a9.
- Kiểm tra cache container đã có config và trọng số PhoBERT trước khi gọi; không chạy lệnh tải model mới hoặc train NER.
- POST /api/v1/campaigns/search thật trả HTTP 200, 4 chiến dịch miền Bắc đủ bộ lọc/có vector, top 3 có score/model version hợp lệ.
- Đã chạy lại toàn bộ browser workflow qua Django test 8004 trỏ API thật 8001: live_qdrant_tested=true, model_name=vinai/phobert-base-v2, reload/history/logout/mobile đều đạt. Fixture chỉ ở SQLite test, đã dọn sau khi chạy, không tạo Candidate hay ghi campaign/vector trong PostgreSQL/Qdrant.
- Các helper simulation/test server được dừng sau kiểm thử. Web local 5175, Django thật 8002 và matching thật 8001 được để chạy để người dùng thử.

## Chưa nghiệm thu chất lượng

NER hiện rules/manual, chưa PhoBERT NER đã train. Kết quả thử chứng minh tích hợp chạy được, không phải precision/recall/F1 của trích xuất hoặc chất lượng tuyển dụng.

Embedding hiện là PhoBERT mean pooling đang có, chưa fine-tune riêng cho retrieval chiến dịch. Trong một truy vấn điện tử thử nghiệm, nghề may có cosine hơi cao hơn điện tử; không coi điểm cao là đúng nghiệp vụ hoặc xác suất được tuyển. Cần nghiệm thu/reranking theo dữ liệu thực tế trước khi dựa vào thứ tự đề xuất để quyết định.

Ca/ngày bắt đầu, khoảng cách/địa chỉ cụ thể chưa được kiểm chứng bằng dữ liệu có cấu trúc. Không tự gán chiến dịch hay tạo hồ sơ, không thay thế người tư vấn. Cấu hình hiện là local dev, không phải cấu hình phát hành Internet.
