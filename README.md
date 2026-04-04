# clipflow

**Trim, compress, and highlight video clips — powered by ffmpeg subprocess.**

[![Tests](https://github.com/ronaldgosso/clipflow/actions/workflows/test.yml/badge.svg)](https://github.com/ronaldgosso/clipflow/actions/workflows/test.yml)
[![PyPI version](https://img.shields.io/pypi/v/clipflow.svg)](https://pypi.org/project/clipflow/)
[![Python versions](https://img.shields.io/pypi/pyversions/clipflow.svg)](https://pypi.org/project/clipflow/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Typed](https://img.shields.io/badge/typing-py.typed-blue)](clipflow/py.typed)

---

`clipflow` is a zero-dependency Python library and CLI that wraps `ffmpeg` via subprocess to let you trim, compress, crop, and highlight video clips with a clean, typed API.

```python
import clipflow

results = clipflow.trim(
    "documentary.mp4",
    clipflow.ClipSpec(
        clipflow.parse_range("01:00", "02:30"),
        highlight=True,
        compress=clipflow.COMPRESS_HIGH,
        aspect_ratio=clipflow.AR_16_9,
        label="best_scene",
    ),
)

print(results[0])
# ClipResult(✓ 'best_scene' → output/best_scene.mp4 [1.83s])
```

---

## Requirements

- Python 3.9+
- [ffmpeg](https://ffmpeg.org/download.html) installed and on your `PATH`

No Python package dependencies — `clipflow` uses only the standard library.

---

## Installation

```bash
pip install clipflow
```

Verify your ffmpeg installation:

```bash
ffmpeg -version
```

---

## Python API

### `clipflow.trim()`

```python
import clipflow
from clipflow import ClipSpec, parse_range, COMPRESS_HIGH, AR_9_16

# ── 1. Stream-copy trim (lossless, very fast) ──────────────────────────────
results = clipflow.trim(
    "input.mp4",
    ClipSpec(parse_range("00:30", "02:15")),
    output_dir="clips",
)

# ── 2. Multiple ranges in one call ────────────────────────────────────────
clips = [
    ClipSpec(parse_range("00:00", "01:00"), label="intro"),
    ClipSpec(parse_range("10:30", "12:00"), label="climax"),
    ClipSpec(parse_range("58:00", "60:00"), label="outro"),
]
results = clipflow.trim("lecture.mp4", clips, output_dir="out")

# ── 3. Compress + aspect ratio + highlight ────────────────────────────────
results = clipflow.trim(
    "raw_footage.mp4",
    ClipSpec(
        parse_range("05:00", "06:30"),
        highlight=True,          # also saved to out/highlights/
        compress=COMPRESS_HIGH,  # CRF 18, slow preset — best quality
        aspect_ratio=AR_9_16,    # crop/pad to vertical 9:16 (Reels/Shorts)
        label="hero_moment",
    ),
    output_dir="out",
)
print(results[0].highlight_path)
# PosixPath('out/highlights/hero_moment.mp4')

# ── 4. Progress callback ───────────────────────────────────────────────────
def on_progress(idx, total, result):
    status = "✓" if result.ok else "✗"
    print(f"[{idx}/{total}] {status} {result.spec.effective_label()}")

clipflow.trim("video.mp4", clips, output_dir="out", on_progress=on_progress)
```

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

### `clipflow.batch()`

```python
from pathlib import Path
from clipflow import BatchSpec, ClipSpec, parse_range

specs = [
    BatchSpec(
        input_path=Path("ep01.mp4"),
        output_dir=Path("ep01_clips"),
        clips=[
            ClipSpec(parse_range("00:30", "01:30"), label="cold_open"),
            ClipSpec(parse_range("20:00", "21:00"), label="twist", highlight=True),
        ],
    ),
    BatchSpec(
        input_path=Path("ep02.mp4"),
        output_dir=Path("ep02_clips"),
        clips=[ClipSpec(parse_range("00:00", "02:00"))],
    ),
]

all_results = clipflow.batch(specs)
for path, results in all_results.items():
    ok = sum(r.ok for r in results)
    print(f"{path.name}: {ok}/{len(results)} clips ok")
```

---

## Time formats

`parse_range()` and `parse_seconds()` accept any of these:

| Input | Seconds |
|---|---|
| `"01:30"` | 90.0 |
| `"01:02:03"` | 3723.0 |
| `"90"` | 90.0 |
| `"90.5"` | 90.5 |
| `90` (int) | 90.0 |
| `90.5` (float) | 90.5 |

---

## Compression presets

| Constant | CRF | Speed preset | Use case |
|---|---|---|---|
| `COMPRESS_LOW` | 28 | fast | Smallest file, visible quality loss |
| `COMPRESS_MEDIUM` | 23 | medium | Balanced (ffmpeg default) |
| `COMPRESS_HIGH` | 18 | slow | Best quality, largest file |

Or build your own:

```python
from clipflow import CompressOptions

custom = CompressOptions(
    crf=20,
    preset="slower",
    codec="libx265",        # H.265 — smaller than H.264 at same quality
    audio_bitrate="192k",
)
```

---

## Aspect ratio shortcuts

| Constant | Ratio | Use case |
|---|---|---|
| `AR_16_9` | 16:9 | YouTube, landscape |
| `AR_9_16` | 9:16 | Reels, Shorts, TikTok |
| `AR_1_1` | 1:1 | Instagram square |
| `AR_4_3` | 4:3 | Classic TV / older formats |

Custom ratio:

```python
from clipflow import AspectRatio

ultra_wide = AspectRatio(21, 9)
```

---

## CLI

```
clipflow COMMAND [OPTIONS]
```

### `clipflow trim`

```bash
# Lossless stream-copy (default — fastest)
clipflow trim lecture.mp4 01:00-02:30

# Multiple ranges
clipflow trim lecture.mp4 00:00-01:00 10:30-12:00 --output clips/

# Compress to H.264 high quality, crop to 9:16, mark as highlight
clipflow trim concert.mp4 05:00-06:30 \
    --compress high \
    --aspect 9:16 \
    --highlight \
    --output out/

# Custom CRF with H.265 codec
clipflow trim raw.mp4 00:00-30:00 --crf 20 --codec libx265

# Name the output file
clipflow trim video.mp4 01:00-02:00 --label my_clip
```

### `clipflow inspect`

```bash
# Human-readable metadata
clipflow inspect documentary.mp4

# Machine-readable JSON (pipe-friendly)
clipflow inspect documentary.mp4 --json | jq .duration_fmt
```

### `clipflow batch`

Create a `spec.json`:

```json
[
  {
    "input": "lecture.mp4",
    "output_dir": "clips/lecture",
    "clips": [
      {
        "start": "00:30",
        "end":   "02:15",
        "label": "intro",
        "highlight": false,
        "compress": "medium"
      },
      {
        "start": "10:00",
        "end":   "11:30",
        "label": "key_moment",
        "highlight": true,
        "aspect": "16:9"
      }
    ]
  }
]
```

```bash
clipflow batch spec.json
```

---

## API reference

### `clipflow.trim(input_path, clips, *, output_dir, on_progress)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `input_path` | `str \| Path` | required | Source video file |
| `clips` | `ClipSpec \| list[ClipSpec]` | required | Segment(s) to extract |
| `output_dir` | `str \| Path` | `"output"` | Destination directory |
| `on_progress` | `callable \| None` | `None` | Called after each clip: `(idx, total, result)` |

Returns `list[ClipResult]`.

### `clipflow.inspect(input_path)`

Returns `VideoInfo` with: `path`, `duration_s`, `duration_fmt`, `width`, `height`, `resolution`, `fps`, `video_codec`, `audio_codec`, `size_bytes`, `size_mb`.

### `clipflow.batch(specs, *, on_progress)`

Returns `dict[Path, list[ClipResult]]` keyed by resolved input path.

---

## How it works

`clipflow` builds and runs `ffmpeg` commands as subprocess calls — no Python video library is involved. The key insight is that ffmpeg has two seek modes:

**Stream-copy (default):** `-ss` is placed *before* `-i`, enabling a fast keyframe seek. The output is produced by copying codec bytes directly — no re-encoding, no quality loss, very fast.

**Re-encode (with `compress=`):** `-ss` is placed *after* `-i`, giving frame-accurate cuts. The video is decoded and re-encoded with the chosen CRF and preset.

The highlight mechanism copies the finished clip to `output/highlights/` using `shutil.copy2` — no second ffmpeg invocation.

---

## Development

```bash
git clone https://github.com/ronaldgosso/clipflow.git
cd clipflow
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check clipflow/ tests/

# Format
black clipflow/ tests/

# Type check
mypy clipflow/ --ignore-missing-imports
```

---

## License

MIT © [Ronald Isack Gosso](https://github.com/ronaldgosso)
