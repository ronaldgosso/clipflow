# Changelog

All notable changes to `clipflow` are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [0.1.0] — 2025-01-01

### Added
- `clipflow.trim()` — trim one or more time ranges from a video file
  - Stream-copy mode (lossless, fast) when no compression is requested
  - Re-encode mode with configurable CRF, preset, and codec
  - Highlight routing: clips marked `highlight=True` are copied to `output/highlights/`
  - Aspect ratio crop/pad: `AR_16_9`, `AR_9_16`, `AR_1_1`, `AR_4_3`, or custom `AspectRatio`
  - Per-clip `on_progress` callback `(idx, total, ClipResult) -> None`
- `clipflow.inspect()` — return `VideoInfo` metadata via ffprobe
- `clipflow.batch()` — process multiple `BatchSpec` objects across different source files
- `parse_range()` and `parse_seconds()` — accept `MM:SS`, `HH:MM:SS`, plain seconds (str/int/float)
- Named compression presets: `COMPRESS_LOW`, `COMPRESS_MEDIUM`, `COMPRESS_HIGH`
- CLI: `clipflow trim`, `clipflow inspect`, `clipflow batch`
  - ANSI colour output, auto-disabled when output is piped
  - `clipflow inspect --json` for machine-readable metadata
  - `clipflow batch spec.json` for JSON-driven batch processing
- Full type annotations, `py.typed` marker (PEP 561)
- Zero runtime dependencies — only stdlib + system ffmpeg required
- CI: test matrix Python 3.9–3.12 on Ubuntu and Windows via GitHub Actions
- CD: OIDC trusted publishing to PyPI on version tag push

[Unreleased]: https://github.com/ronaldgosso/clipflow/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/ronaldgosso/clipflow/releases/tag/v0.1.0
