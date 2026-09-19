FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml README.md ./
COPY app ./app
COPY alembic ./alembic
COPY scripts ./scripts
COPY alembic.ini ./

ARG INSTALL_EMBEDDINGS=false
ARG TORCH_CPU_VERSION=2.6.0+cpu
RUN --mount=type=cache,target=/root/.cache/pip \
    if [ "$INSTALL_EMBEDDINGS" = "true" ]; then \
      pip install --timeout 180 --retries 8 --index-url https://download.pytorch.org/whl/cpu "torch==$TORCH_CPU_VERSION" && \
      pip install --timeout 180 --retries 8 --no-deps . && \
      pip install --timeout 180 --retries 8 "transformers>=4.44,<5.0"; \
    else \
      pip install --no-cache-dir --no-deps .; \
    fi

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
