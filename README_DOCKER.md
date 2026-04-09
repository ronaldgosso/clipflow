<div align="center">

# clipflow — Docker Image

[![Docker Pulls](https://img.shields.io/docker/pulls/ronaldgosso/clipflow?style=for-the-badge&logo=docker&labelColor=111&color=0969da)](https://hub.docker.com/r/ronaldgosso/clipflow)
[![Docker Image Size](https://img.shields.io/docker/image-size/ronaldgosso/clipflow/latest?style=for-the-badge&logo=docker&labelColor=111&color=0969da)](https://hub.docker.com/r/ronaldgosso/clipflow/tags)
[![Docker Tags](https://img.shields.io/badge/tags-latest%2C%20v0.3.1-0969da?style=for-the-badge&labelColor=111&logo=docker)](https://hub.docker.com/r/ronaldgosso/clipflow/tags)

**Trim · Compress · Highlight** — zero setup, instant video clipping with auto-managed ffmpeg.

[GitHub Repository](https://github.com/ronaldgosso/clipflow) · [PyPI](https://pypi.org/project/clipflow/) · [Homepage](https://ronaldgosso.github.io/clipflow)

<br />

<img width="100" alt="clipflow logo" src="https://raw.githubusercontent.com/ronaldgosso/clipflow/main/docs/icon.svg" />

</div>

---

## Overview

`clipflow` is a typed Python API and CLI for video clipping with auto-managed ffmpeg. This Docker image provides a ready-to-use environment for video processing without any installation or configuration.

**Features:**
- ⚡ **Lossless stream-copy** — trim 10 GB files in seconds with zero quality loss
- 🎬 **Frame-accurate re-encode** when you need compression
- ✨ **Highlight routing** — first-class concept missing from every other package
- 📦 **Zero runtime dependencies** — stdlib + system ffmpeg, nothing else
- 🐳 **Multi-stage build** — optimized slim production image (~150MB)

---

## Quick Start

### Pull the image

```bash
docker pull ronaldgosso/clipflow:latest
```

### Basic usage

```bash
# Trim a video (lossless stream-copy)
docker run --rm -v /path/to/videos:/data ronaldgosso/clipflow:latest \
  trim video.mp4 00:00-01:00

# Compress + aspect ratio + highlight
docker run --rm -v /path/to/videos:/data ronaldgosso/clipflow:latest \
  trim raw_footage.mp4 05:00-06:30 --compress high --aspect 9:16 --highlight

# Inspect metadata
docker run --rm -v /path/to/videos:/data ronaldgosso/clipflow:latest \
  inspect documentary.mp4
```

### Using Docker Compose

Create a `docker-compose.yml`:

```yaml
services:
  clipflow:
    image: ronaldgosso/clipflow:latest
    volumes:
      - ./videos:/data
    working_dir: /data
```

Then run:

```bash
docker compose run --rm clipflow trim video.mp4 00:30-02:15
```

---

## Docker Compose (Development)

For development with hot-reload and full test suite, use the [official repository](https://github.com/ronaldgosso/clipflow):

```bash
git clone https://github.com/ronaldgosso/clipflow.git
cd clipflow

# Run full test suite
docker compose run --rm test

# Development shell
docker compose run --rm dev

# Quick lint checks
docker compose run --rm lint
```

---

## Volume Mounts

| Host Path | Container Path | Purpose |
|---|---|---|
| `/path/to/videos` | `/data` | Input/output video files |
| *(auto)* | `/app/.cache` | FFmpeg cache (internal) |

**Important:** Always mount `/data` to access your video files inside the container.

---

## CLI Commands

All `clipflow` CLI commands are available:

```bash
# Lossless trim
clipflow trim lecture.mp4 01:00-02:30

# Multiple ranges
clipflow trim lecture.mp4 00:00-01:00 10:30-12:00 --output clips/

# Compress + crop + highlight
clipflow trim concert.mp4 05:00-06:30 --compress high --aspect 9:16 --highlight

# Custom CRF + H.265
clipflow trim raw.mp4 00:00-30:00 --crf 20 --codec libx265

# Inspect metadata
clipflow inspect documentary.mp4

# Batch from JSON spec
clipflow batch spec.json
```

---

## Python API (in Docker)

You can also use the Python API interactively:

```bash
docker run --rm -it -v /path/to/videos:/data ronaldgosso/clipflow:latest python
```

```python
import clipflow
from clipflow import ClipSpec, parse_range, COMPRESS_HIGH, AR_9_16

# Lossless trim
results = clipflow.trim(
    "input.mp4",
    ClipSpec(parse_range("00:30", "02:15")),
    output_dir="clips",
)

# Compress + aspect ratio + highlight
results = clipflow.trim(
    "raw_footage.mp4",
    ClipSpec(
        parse_range("05:00", "06:30"),
        highlight=True,
        compress=COMPRESS_HIGH,
        aspect_ratio=AR_9_16,
        label="hero_moment",
    ),
    output_dir="out",
)
```

---

## Image Details

| Property | Value |
|---|---|
| **Base Image** | `python:3.11-slim` |
| **Python Version** | 3.11 |
| **FFmpeg** | System package (apt) |
| **Image Size** | ~150MB (slim runtime) |
| **Architecture** | linux/amd64, linux/arm64 |
| **Entrypoint** | `clipflow` |

---

## Tags

| Tag | Description |
|---|---|
| `latest` | Latest stable release (recommended) |
| `v0.3.1` | Specific version pin |
| `main` | Latest development build |

Browse all available tags: [Docker Hub Tags](https://hub.docker.com/r/ronaldgosso/clipflow/tags)

---

## CI/CD Integration

This image is automatically built and pushed via GitHub Actions on every commit to `main` and on version tags.

### GitHub Actions Workflow

```yaml
name: Docker

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          push: true
          tags: |
            ronaldgosso/clipflow:latest
            ronaldgosso/clipflow:${{ github.ref_name }}
```

---

## Links

- [GitHub Repository](https://github.com/ronaldgosso/clipflow)
- [PyPI Package](https://pypi.org/project/clipflow/)
- [Homepage](https://ronaldgosso.github.io/clipflow)
- [Documentation](https://github.com/ronaldgosso/clipflow/blob/main/README.md)
- [Bug Reports](https://github.com/ronaldgosso/clipflow/issues)
- [Google Colab](https://colab.research.google.com/drive/1LWJ2GmCZLqmKXmJ25lBR5uFX5tmXK7OJ?usp=sharing)

---

## License

MIT © [Ronald Isack Gosso](https://github.com/ronaldgosso)

<div align="center"><sub>Built with Python · auto-managed ffmpeg · subprocess · zero magic</sub></div>
