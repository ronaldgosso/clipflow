# Docker Setup for clipflow

[![Docker Build](https://github.com/ronaldgosso/clipflow/actions/workflows/docker.yml/badge.svg)](https://github.com/ronaldgosso/clipflow/actions/workflows/docker.yml)
[![Docker Image](https://img.shields.io/badge/docker-ronaldgosso/clipflow-0969da?logo=docker)](https://hub.docker.com/r/ronaldgosso/clipflow)

Complete Docker setup for development, testing, and production deployment with automated CI/CD pipelines.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- Docker Compose v2+ (included with Docker Desktop)

## Quick Start

### Run tests (zero setup)

```bash
docker compose run --rm test
```

### Build the image

```bash
docker build -t clipflow:latest .
```

### Use the CLI

```bash
# Show help
docker run --rm clipflow:latest --help

# Trim a video (mount your videos directory)
docker run --rm -v /path/to/videos:/data clipflow:latest trim video.mp4 00:00-01:00

# Inspect metadata
docker run --rm -v /path/to/videos:/data clipflow:latest inspect video.mp4
```

## Docker Compose Services

### Run tests

```bash
docker compose run --rm test
```

### Run linting only

```bash
docker compose run --rm lint
```

### Interactive development shell

```bash
docker compose run --rm dev
```

## Production Deployment

### Docker Hub

Images are automatically built and pushed to Docker Hub on every push to `main` and releases:

```bash
# Pull latest
docker pull ronaldgosso/clipflow:latest

# Pull specific version
docker pull ronaldgosso/clipflow:0.3.1
```

### Run production container

```bash
docker run --rm \
  -v /path/to/videos:/data \
  ronaldgosso/clipflow:latest \
  trim input.mp4 00:00-01:00
```

## CI/CD Integration

The CI workflow runs automatically on push and PR:

1. **Docker Build & Test** — Builds image and runs full test suite
2. **Native Matrix Tests** — Tests across Python versions and OS
3. **Docker Publish** — Pushes to Docker Hub on releases (via `docker.yml`)

### Required Secrets

To enable Docker Hub publishing, add these repository secrets:

| Secret | Value |
|--------|-------|
| `DOCKERHUB_USERNAME` | Your Docker Hub username (e.g., `ronaldgosso`) |
| `DOCKERHUB_TOKEN` | Docker Hub access token with Read & Write permissions |

**How to create the token:**
1. Go to [hub.docker.com](https://hub.docker.com) → Account Settings → Security
2. Click **New Access Token** → Name it (e.g., `GitHub CI`)
3. Set permissions: **Read & Write**
4. Copy the token and add it to GitHub → Settings → Secrets → Actions → New repository secret

### Trigger manually

```bash
# Build and test locally with docker compose
docker compose run --rm test

# Or build and run manually
docker build -t clipflow:test --target builder .
docker run --rm clipflow:test bash -c "ruff check clipflow tests && black --check clipflow tests && mypy clipflow && pytest -v"
```

## Volume Mounts

| Path | Purpose |
|------|---------|
| `/data` | Input/output videos directory |
| `/app/.cache` | FFmpeg cache persistence |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CLIPFLOW_CACHE_DIR` | `/app/.cache` | FFmpeg binary cache location |
| `PYTHONUNBUFFERED` | `1` | Unbuffered Python output |

## Multi-stage Build

- **builder**: Installs dev dependencies, runs tests, linting, type checks
- **runtime**: Slim production image with only runtime dependencies

## Troubleshooting

### Docker not running

Start Docker Desktop before running any docker commands.

### Permission denied on mounted volumes

Ensure your video files have proper read permissions on the host system.

### FFmpeg cache miss

The container will auto-download FFmpeg on first use. To pre-cache:

```bash
docker run --rm clipflow:latest python -c "import clipflow; clipflow.setup_ffmpeg()"
```
