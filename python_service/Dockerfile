# ============================================================
# Stage 1: Build — cài dependencies bằng uv (nhanh hơn pip)
# ============================================================
FROM python:3.12-slim AS builder

# Cài uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy file dependency trước → tận dụng Docker layer cache
COPY pyproject.toml uv.lock ./

# Cài dependencies vào .venv trong container
RUN uv sync --frozen --no-dev --no-install-project

# ============================================================
# Stage 2: Runtime — image nhẹ, chỉ chứa code + deps
# ============================================================
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy virtual env đã build từ stage 1
COPY --from=builder /app/.venv /app/.venv

# Đảm bảo dùng Python từ venv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8

# Copy toàn bộ source code
COPY . .

# Tạo thư mục logs & data nếu chưa có
RUN mkdir -p logs data/chroma_db

# Render truyền PORT qua env, mặc định 8000
ENV PORT=8000

EXPOSE ${PORT}

# Khởi chạy FastAPI bằng uvicorn
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
