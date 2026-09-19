# Dữ liệu 004

Không tạo bảng mới. Đặc tả dùng hai bảng đã có:

| Bảng | Vai trò |
| --- | --- |
| `model_versions` | Khóa identity của mô hình, version và dimension thực tế. |
| `embedding_refs` | Sẽ lưu profile hash và point Qdrant ở Spec 005. |

## Profile hash

```text
SHA-256(normalized_profile_text + "|" + model_version_id)
```

Hash thay đổi khi text quyết định hoặc model version thay đổi. Nhờ đó phase rebuild có thể bỏ qua object không đổi.
