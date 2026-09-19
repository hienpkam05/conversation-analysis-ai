# Mô hình dữ liệu: Đặc tả 002

| Bảng | Vai trò |
| --- | --- |
| `candidates` | Hồ sơ ứng viên phục vụ matching. |
| `recruiters` | Năng lực, workload, conversion rate và trạng thái tư vấn viên. |
| `recruiter_regions` | Vùng/tỉnh phụ trách của recruiter. |
| `campaigns` | Thông tin chiến dịch tuyển dụng. |
| `recruiter_campaigns` | Quan hệ N:N recruiter và campaign. |
| `model_versions` | Phiên bản model/dimension phục vụ tái lập thí nghiệm. |
| `embedding_refs` | Liên kết bản ghi PostgreSQL với point Qdrant ở đặc tả sau. |
| `matching_runs` | Snapshot mỗi lần matching ở đặc tả sau. |
| `matching_results` | Điểm, lý do và trạng thái chọn của từng kết quả. |

## Ràng buộc chính

- `current_workload >= 0`, `max_workload > 0`.
- `conversion_rate` trong `[0, 1]` nếu có dữ liệu.
- `salary_min <= salary_max` nếu cả hai tồn tại.
- `matching_results` unique theo `(run_id, recruiter_id)` và `(run_id, rank)`.
- `embedding_refs` unique theo object, model version và loại embedding.
- Không có trường PII trong `embedding_refs` hoặc dữ liệu chuẩn bị cho Qdrant.
