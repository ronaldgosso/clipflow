<div align="center">

<br />

```
       ██████╗██╗     ██╗██████╗ ███████╗██╗      ██████╗ ██╗    ██╗
      ██╔════╝██║     ██║██╔══██╗██╔════╝██║     ██╔═══██╗██║    ██║
      ██║     ██║     ██║██████╔╝█████╗  ██║     ██║   ██║██║ █╗ ██║
      ██║     ██║     ██║██╔═══╝ ██╔══╝  ██║     ██║   ██║██║███╗██║
      ╚██████╗███████╗██║██║     ██║     ███████╗╚██████╔╝╚███╔███╔╝
       ╚═════╝╚══════╝╚═╝╚═╝     ╚═╝     ╚══════╝ ╚═════╝  ╚══╝╚══╝
```

**Trim · Compress · Highlight**

Typed Python API and CLI for video clipping — auto-managed ffmpeg, zero setup.
Zero runtime dependencies. Now with Docker support for instant development.

<br />

[![Tests](https://github.com/ronaldgosso/clipflow/actions/workflows/ci.yml/badge.svg)](https://github.com/ronaldgosso/clipflow/actions/workflows/ci.yml)
[![Docker](https://github.com/ronaldgosso/clipflow/actions/workflows/docker.yml/badge.svg)](https://github.com/ronaldgosso/clipflow/pkgs/container/clipflow)
[![PyPI version](https://img.shields.io/pypi/v/clipflow?color=f5a623&labelColor=111)](https://pypi.org/project/clipflow/)
[![Python versions](https://img.shields.io/pypi/pyversions/clipflow?labelColor=111)](https://pypi.org/project/clipflow/)
[![Coverage](https://img.shields.io/badge/coverage-91%25-4caf7d?labelColor=111)](https://github.com/ronaldgosso/clipflow/actions)
[![License: MIT](https://img.shields.io/badge/license-MIT-888?labelColor=111)](LICENSE)
[![Typed](https://img.shields.io/badge/typed-py.typed-82aaff?labelColor=111)](clipflow/py.typed)
[![Docker Image](https://img.shields.io/badge/docker-ghcr.io-0969da?labelColor=111&logo=docker)](https://github.com/ronaldgosso/clipflow/pkgs/container/clipflow)
[![Homepage](https://img.shields.io/badge/homepage-ronaldgosso.github.io%2Fclipflow-f5a623?labelColor=111)](https://ronaldgosso.github.io/clipflow)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1LWJ2GmCZLqmKXmJ25lBR5uFX5tmXK7OJ?usp=sharing)
[![Downloads](https://img.shields.io/pypi/dm/clipflow.svg)](https://pypi.org/project/clipflow/)

<br />

<img width="881" height="367" alt="CUTfLOW logo" src="https://github.com/user-attachments/assets/0aa6cb4e-f517-41ac-b428-01b756674d4d" />

</div>

---

## Why clipflow?

Most Python video libraries convert frames to NumPy arrays — slow, memory-heavy, and unnecessary for trimming. `clipflow` builds and runs `ffmpeg` commands directly as subprocess calls:

- **Lossless stream-copy** — trimming a 10 GB file takes seconds with zero quality loss
- **Frame-accurate re-encode** when you need compression
- **Highlight routing** — a first-class concept missing from every other package
- **Clean typed API** — all inputs and outputs are typed dataclasses, no dicts
- **Zero runtime dependencies** — stdlib + system ffmpeg, nothing else

---

## Installation

### Option 1: pip (Traditional)

```bash
pip install clipflow
```

**Requires:** Python ≥ 3.9

### Option 2: Docker (Zero Setup)

```bash
# Pull pre-built image
docker pull ghcr.io/ronaldgosso/clipflow:latest

# Run tests instantly
docker compose run --rm test

# Use CLI
docker run --rm -v /path/to/videos:/data ghcr.io/ronaldgosso/clipflow:latest trim video.mp4 00:00-01:00
```

No Python installation required! See [DOCKER.md](DOCKER.md) for complete Docker setup.

---

**FFmpeg:** Automatically downloaded and managed on first use — no manual installation required! 🎉

### How FFmpeg Management Works

On first use, `clipflow` automatically:
1. Detects your platform (Windows, macOS, or Linux)
2. Downloads the appropriate FFmpeg binaries from trusted sources
3. Caches them locally for future use
4. Falls back to system PATH if you already have FFmpeg installed

You can also pre-download FFmpeg explicitly:

```python
import clipflow

# Optional: Pre-download FFmpeg (happens automatically on first use anyway)
clipflow.setup_ffmpeg()

# Check where FFmpeg is located 
print(clipflow.get_ffmpeg_path())
print(clipflow.get_ffprobe_path())
```

**Cache location:**
- **Windows**: `%LOCALAPPDATA%\clipflow\ffmpeg\`
- **macOS**: `~/Library/Caches/clipflow/ffmpeg/`
- **Linux**: `~/.cache/clipflow/ffmpeg/`

If you prefer to use your system FFmpeg, ensure it's on your PATH — clipflow will use it automatically.

### Manual FFmpeg Installation (Optional)

If you want to install FFmpeg manually or use a specific version:

```bash
# Windows — via Chocolatey
choco install ffmpeg

# Windows — via winget
winget install Gyan.FFmpeg

# macOS — via Homebrew
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Fedora
sudo dnf install ffmpeg
```

---

## Quick start

```python
import clipflow

results = clipflow.trim(
    "documentary.mp4",
    clipflow.ClipSpec(clipflow.parse_range("01:00", "02:30")),
)
print(results[0])
# ClipResult(✓ 'clip_01' → output/clip_01.mp4 [0.43s])
```

```bash
clipflow trim documentary.mp4 01:00-02:30
```

---

## Python API

### `clipflow.trim()`

```python
import clipflow
from clipflow import ClipSpec, parse_range, COMPRESS_HIGH, AR_9_16

# Lossless stream-copy
results = clipflow.trim(
    "input.mp4",
    ClipSpec(parse_range("00:30", "02:15")),
    output_dir="clips",
)

# Multiple ranges
clips = [
    ClipSpec(parse_range("00:00", "01:00"), label="intro"),
    ClipSpec(parse_range("10:30", "12:00"), label="climax"),
    ClipSpec(parse_range("58:00", "60:00"), label="outro"),
]
results = clipflow.trim("lecture.mp4", clips, output_dir="out")

# Compress + aspect ratio + highlight
results = clipflow.trim(
    "raw_footage.mp4",
    ClipSpec(
        parse_range("05:00", "06:30"),
        highlight=True,          # copied to out/highlights/ automatically
        compress=COMPRESS_HIGH,  # CRF 18, slow preset
        aspect_ratio=AR_9_16,    # crop/pad to 9:16 for Reels/Shorts
        label="hero_moment",
    ),
    output_dir="out",
)
print(results[0].highlight_path)  # out/highlights/hero_moment.mp4

# Progress callback
def on_progress(idx, total, result):
    print(f"[{idx}/{total}] {'✓' if result.ok else '✗'} {result.spec.effective_label()}")

clipflow.trim("video.mp4", clips, output_dir="out", on_progress=on_progress)
```

**`ClipResult` fields:**

| Field | Type | Description |
|---|---|---|
| `ok` | `bool` | `True` if clip was produced without error |
| `output_path` | `Path \| None` | Absolute path to the output file |
| `highlight_path` | `Path \| None` | Path to highlight copy, or `None` |
| `duration_s` | `float` | Wall-clock seconds the ffmpeg call took |
| `error` | `str \| None` | Error message if `ok` is `False` |

---

### `clipflow.inspect()`

```python
info = clipflow.inspect("documentary.mp4")

print(info.resolution)    # '1920×1080'
print(info.duration_fmt)  # '01:23:45'
print(info.fps)           # 29.97
print(info.video_codec)   # 'h264'
print(info.audio_codec)   # 'aac'
print(info.size_mb)       # 842.3
```

---

### `clipflow.batch()`

```python
from pathlib import Path
from clipflow import BatchSpec, ClipSpec, parse_range
import clipflow

specs = [
    BatchSpec(
        input_path=Path("ep01.mp4"),
        output_dir=Path("ep01_clips"),
        clips=[
            ClipSpec(parse_range("00:30", "01:30"), label="cold_open"),
            ClipSpec(parse_range("20:00", "21:00"), label="twist", highlight=True),
        ],
    ),
]
all_results = clipflow.batch(specs)
```

---

## CLI

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
clipflow inspect documentary.mp4 --json | jq .fps

# Batch from JSON spec
clipflow batch spec.json
```

**`spec.json` format:**

```json
[
  {
    "input": "lecture.mp4",
    "output_dir": "clips",
    "clips": [
      { "start": "00:30", "end": "02:15", "label": "intro", "compress": "medium" },
      { "start": "10:00", "end": "11:30", "highlight": true, "aspect": "16:9" }
    ]
  }
]
```

---

## Time formats

All time inputs accept:

| Format | Example | Seconds |
|---|---|---|
| `"MM:SS"` | `"01:30"` | 90.0 |
| `"HH:MM:SS"` | `"01:02:03"` | 3723.0 |
| `"SS"` | `"90"` | 90.0 |
| `int` / `float` | `90` / `90.5` | 90.0 / 90.5 |

---

## Compression presets

| Constant | CRF | Speed | Use case |
|---|---|---|---|
| `COMPRESS_LOW` | 28 | fast | Smallest file |
| `COMPRESS_MEDIUM` | 23 | medium | Balanced (ffmpeg default) |
| `COMPRESS_HIGH` | 18 | slow | Best quality |

Custom:

```python
from clipflow import CompressOptions

custom = CompressOptions(crf=20, preset="slower", codec="libx265", audio_bitrate="192k")
```

---

## Aspect ratio shortcuts

| Constant | Ratio | Use case |
|---|---|---|
| `AR_16_9` | 16:9 | YouTube, landscape |
| `AR_9_16` | 9:16 | Reels, Shorts, TikTok |
| `AR_1_1` | 1:1 | Instagram square |
| `AR_4_3` | 4:3 | Classic TV |

```python
from clipflow import AspectRatio
ultra_wide = AspectRatio(21, 9)
```

---

## How it works

`clipflow` builds ffmpeg commands as `list[str]` and runs them with `subprocess.run`.

**FFmpeg Management:**
On first use, clipflow automatically downloads and caches FFmpeg binaries for your platform. The binaries are stored in a local cache directory and reused on subsequent runs. If you have FFmpeg on your PATH, clipflow will use your system installation instead.

**Stream-copy (default — lossless, fast):**
```
ffmpeg -y -ss <start> -t <duration> -i input.mp4 -c copy output.mp4
```
`-ss` before `-i` = keyframe seek. Bytes are copied directly, no re-encoding.

**Re-encode (with `compress=`):**
```
ffmpeg -y -i input.mp4 -ss <start> -t <duration> -c:v libx264 -crf 23 -preset medium -c:a copy output.mp4
```
`-ss` after `-i` = frame-accurate cut. Required when the encoder needs full frame data.

**Highlights:** `shutil.copy2` of the finished clip to `output/highlights/`. No second ffmpeg call.

The entire subprocess layer is isolated in `clipflow/_ffmpeg.py` — no other module touches `subprocess`.

---

## Development

### Local Setup

```bash
git clone https://github.com/ronaldgosso/clipflow.git
cd clipflow
pip install -e ".[dev]"

pytest                                           # 82 tests
pytest --cov=clipflow --cov-report=term          # coverage (>90%)
ruff check clipflow/ tests/ && black clipflow/   # lint + format
mypy clipflow/ --ignore-missing-imports          # strict types
```

### Docker Setup

No Python installation required! Use Docker for instant development:

```bash
# Run full test suite in Docker
docker compose run --rm test

# Development shell with hot-reload
docker compose run --rm dev

# Use CLI via Docker
docker run --rm -v /path/to/videos:/data clipflow:latest trim video.mp4 00:00-01:00

# Pull pre-built image from GitHub Container Registry
docker pull ghcr.io/ronaldgosso/clipflow:latest
```

See [DOCKER.md](DOCKER.md) for complete Docker documentation including CI/CD integration and production deployment.

**Note:** FFmpeg binaries are automatically managed. Tests mock the FFmpeg manager to avoid actual downloads.

**Release:**

```bash
# Bump version in pyproject.toml + clipflow/__init__.py, then:
git tag v0.3.0 && git push origin v0.3.0
# publish.yml triggers → PyPI via OIDC + Docker image to GHCR
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## License

MIT © [Ronald Isack Gosso](https://github.com/ronaldgosso)

<div align="center"><sub>Built with Python · auto-managed ffmpeg · subprocess · zero magic</sub></div>
