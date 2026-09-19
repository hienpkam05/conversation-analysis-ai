# Chạy Spec 004

Từ thư mục `matching_service`, cài thêm dependency ML khi cần gọi provider thật:

```powershell
pip install -e ".[embeddings,dev]"
```

Cấu hình PhoBERT trong `.env`:

```env
EMBEDDING_PROVIDER=phobert
EMBEDDING_MODEL=vinai/phobert-base-v2
EMBEDDING_MODEL_VERSION=meanpool-v1
EMBEDDING_DEVICE=cpu
EMBEDDING_MAX_LENGTH=256
EMBEDDING_BATCH_SIZE=16
```

Để thử baseline Sentence Transformers, thay provider và model:

```env
EMBEDDING_PROVIDER=sentence_transformer
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

Sau đó cài extra riêng:

```powershell
pip install -e ".[sentence-transformers]"
```

Chạy test không cần tải model:

```powershell
pytest -q
```

Lần đầu `encode()` tải model từ Hugging Face và có thể mất vài phút. Spec 005 sẽ thêm script rebuild embeddings và Qdrant collection.
