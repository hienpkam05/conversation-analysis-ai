# Mô hình dữ liệu: Đặc tả 001 - Nền tảng Matching

## Mục đích

Đặc tả 001 chưa tạo schema nghiệp vụ đầy đủ.

File này chỉ ghi các quyết định nền tảng về dữ liệu để chuẩn bị cho Đặc tả 002.

## Database

PostgreSQL là nguồn dữ liệu nghiệp vụ chính.

Ví dụ connection URL:

```env
DATABASE_URL=postgresql+asyncpg://app:app@postgres:5432/recruitment_ai
```

## SQLAlchemy Base

Service phải định nghĩa một declarative base dùng chung:

```python
class Base(DeclarativeBase):
    pass
```

Tất cả model trong các đặc tả sau phải kế thừa từ base này.

## Bảng trong Đặc tả 001

Đặc tả 001 chưa cần bảng nghiệp vụ.

Tuy nhiên Alembic phải được cấu hình sẵn để Đặc tả 002 thêm các bảng:

- candidates
- recruiters
- recruiter_regions
- campaigns
- recruiter_campaigns
- model_versions
- embedding_refs
- matching_runs
- matching_results

## Qdrant

Qdrant là dependency bắt buộc trong Đặc tả 001.

Chưa cần tạo vector collection thật.

Health endpoint chỉ cần xác nhận Qdrant kết nối được.

Các collection dự kiến ở phase sau:

```text
recruiter_embeddings
campaign_embeddings
candidate_embeddings optional
```

## Ranh giới entity trong phase sau

Đặc tả 002 sẽ định nghĩa relational schema.

Đặc tả 004 sẽ định nghĩa:

- Tên Qdrant collection
- Vector dimension
- Payload index strategy
- Liên kết embedding_refs giữa PostgreSQL và Qdrant

## Quy tắc PII

Dù Đặc tả 001 chưa tạo bảng nghiệp vụ, quy tắc dữ liệu đã chốt:

- Không đưa họ tên, số điện thoại, email, địa chỉ riêng tư vào vector profile.
- Không dùng tuổi/giới tính để xếp hạng recruiter trong V1.
