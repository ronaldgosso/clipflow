# =============================================================================
# clipflow — Multi-stage Dockerfile
# =============================================================================
# Stage 1: Build & test
# Stage 2: Slim production runtime
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1 — Build environment
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies and ffmpeg for tests
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir --prefix=/install ".[dev]"

# Copy source code
COPY . .

# Run quality checks
RUN ruff check clipflow tests \
    && black --check clipflow tests \
    && mypy clipflow \
    && pytest --tb=short -v --cov=clipflow --cov-report=term

# ---------------------------------------------------------------------------
# Stage 2 — Production runtime
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

LABEL maintainer="Ronald Isack Gosso <ronaldgosso@gmail.com>"
LABEL description="Trim, compress, and highlight video clips — auto-managed ffmpeg"
LABEL version="0.3.0"

WORKDIR /app

# Install runtime ffmpeg
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY --from=builder /app/clipflow ./clipflow
COPY --from=builder /app/pyproject.toml ./pyproject.toml
COPY --from=builder /app/README.md ./README.md

# Create volume mount point for video processing
VOLUME ["/data"]

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    CLIPFLOW_CACHE_DIR=/app/.cache

# Create cache directory
RUN mkdir -p /app/.cache

# Default command
ENTRYPOINT ["clipflow"]
CMD ["--help"]
