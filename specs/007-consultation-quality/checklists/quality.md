# Checklist chất lượng đặc tả 007

## Kiểm tra tài liệu

- [x] Có mục tiêu, phạm vi và tiêu chí nghiệm thu.
- [x] Tên 5 tiêu chí đề xuất được phân biệt với yêu cầu đã xác nhận.
- [x] Có giai đoạn dùng thủ công trước và AI sau khi có dữ liệu nhãn.
- [x] Không coi Whisper segment là nhãn người nói.
- [x] Có nhãn không đủ dữ liệu, quy tắc tổng điểm và bằng chứng absence.
- [x] Có phiên bản hội thoại, rubric, model và quy trình sửa kết quả.
- [x] Phân biệt database Django với PostgreSQL của matching.
- [x] Có API, mô hình dữ liệu, tasks và hướng dẫn kiểm thử tương lai.
- [x] Ghi rõ API/model chưa triển khai và chưa có chỉ số chất lượng.

## Điều kiện trước khi nghiệm thu tính năng

- [ ] Rubric và hướng dẫn gán nhãn được duyệt.
- [x] Hoàn tất workflow thủ công local trên Vue và lưu/mở lại được; bản chấm chờ duyệt, chưa phê duyệt nhãn.
- [ ] Kiểm tra quyền truy cập trước khi triển khai dùng chung.
- [ ] Có tập test độc lập và báo cáo model trước phát hành AI.
- [ ] Có bằng chứng và trạng thái cần duyệt cho dự đoán model.
- [ ] Đã kiểm tra đầy đủ các AC và ghi biên bản chạy thật.
