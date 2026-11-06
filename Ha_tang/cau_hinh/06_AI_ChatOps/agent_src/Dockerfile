# ==============================================================================
# Stage 1: Builder sử dụng trình quản lý gói siêu tốc `uv`
# ==============================================================================
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /build
COPY pyproject.toml ./
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install --no-cache -r pyproject.toml

# ==============================================================================
# Stage 2: Runtime tối giản, bảo mật Non-Root (< 80MB RAM khi vận hành)
# ==============================================================================
FROM python:3.12-slim-bookworm AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Tạo user non-root UID 10001 chuẩn Kubernetes PodSecurity Restricted
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /usr/sbin/nologin -M appuser

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY app ./app

USER 10001:10001
EXPOSE 8000

CMD ["python", "-m", "app.main"]

