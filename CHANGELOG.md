# Changelog

All notable changes to `clipflow` are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [0.2.0] — 2026-04-04

### Added
- **Automatic FFmpeg binary management** — FFmpeg is now downloaded and cached on first use
  - Zero manual installation required for end users
  - Platform-specific builds for Windows, macOS, and Linux
  - Local caching to avoid repeated downloads
  - Fallback to system PATH if cached binaries are unavailable
- New public API functions:
  - `clipflow.setup_ffmpeg()` — pre-download FFmpeg explicitly (optional)
  - `clipflow.get_ffmpeg_path()` — get the resolved ffmpeg binary path
  - `clipflow.get_ffprobe_path()` — get the resolved ffprobe binary path
- `ffmpeg-cache/` added to `.gitignore` for downloaded binaries

### Changed
- **Breaking**: `clipflow` no longer requires manual FFmpeg installation
  - FFmpeg binaries are automatically managed via `_ffmpeg_manager.py`
  - Existing functionality remains fully backward compatible
- Updated description to reflect auto-management: "auto-managed ffmpeg, zero setup"
- Improved error messages in `require_ffmpeg()` and `require_ffprobe()`
- All internal FFmpeg commands now use resolved binary paths instead of PATH lookup

### Internal
- New module: `clipflow/_ffmpeg_manager.py` (367 lines)
  - Handles platform detection and binary downloads
  - Downloads from trusted sources (gyan.dev for Windows, johnvansickle.com for Linux)
  - Thread-safe initialization with lazy loading
  - Comprehensive error handling with actionable messages
- Updated `_ffmpeg.py` to use `ensure_ffmpeg()` for binary resolution
- Updated all 82 tests to properly mock the new FFmpeg management layer
  - Added `mock_ffmpeg_manager` auto-use fixture
  - All tests pass with 100% success rate

### Migration Guide
For users upgrading from 0.1.0:
- **No action required** — clipflow will automatically download FFmpeg on first use
- If you already have FFmpeg on PATH, clipflow will still use your system installation
- To pre-download FFmpeg: `import clipflow; clipflow.setup_ffmpeg()`

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

[Unreleased]: https://github.com/ronaldgosso/clipflow/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/ronaldgosso/clipflow/releases/tag/v0.2.0
[0.1.0]: https://github.com/ronaldgosso/clipflow/releases/tag/v0.1.0
