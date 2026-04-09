# Changelog

All notable changes to `clipflow` are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [0.3.1] — 2026-04-09

### Changed
- Migrate docker image registry from GHCR to Docker Hub (`ronaldgosso/clipflow`)
- Update CI/CD workflows to use Docker Hub with `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` secrets
- Update all documentation to reference Docker Hub URLs

## [0.3.0] — 2026-04-09

### Added
- **Docker support** — full containerization for development, testing, and production
  - Multi-stage Dockerfile with optimized builds
  - Docker Compose with 4 services: `app`, `dev`, `test`, `lint`
  - Zero local Python setup required for contributors
  - Pre-configured FFmpeg in all containers
- **Docker CI/CD automation** — automated container builds and registry pushes
  - New `docker.yml` workflow for Docker Hub publishing
  - Updated `ci.yml` with Docker build & test job
  - GitHub Actions cache optimization for faster builds
  - Multi-platform support (linux/amd64, linux/arm64)
- Comprehensive Docker documentation:
  - `DOCKER.md` — complete setup and usage guide
  - Updated `README.md` with Docker quick start
  - Updated `CONTRIBUTING.md` with Docker development workflows
- `.dockerignore` for optimized build context

### Changed
- Development workflow now supports both local and Docker environments
- CI runs Docker builds in parallel with native matrix tests
- Release process now includes automatic Docker image publishing

### Migration Guide
For users upgrading from 0.2.x:
- **No breaking changes** — all existing functionality remains the same
- **New option**: Use Docker for zero-setup development
- **CI users**: Docker builds run automatically on PRs
- **Production**: Pull from `ghcr.io/ronaldgosso/clipflow` instead of building locally

## [0.2.1] — 2026-04-05

### Added
- **Google Colab support** — one-click notebook for running clipflow in the cloud
  - Pre-configured with FFmpeg and all dependencies
  - Sample usage with sample videos
  - No local installation required
  - Works on Windows, macOS, and Linux

### Changed
- Updated README with Colab badge and usage examples
- Added `notebook.ipynb` with complete Colab workflow
- Updated `CONTRIBUTING.md` with Colab contribution guidelines

### Migration Guide
For users upgrading from 0.2.0:
- **No action required** — clipflow will automatically download FFmpeg on first use
- If you already have FFmpeg on PATH, clipflow will still use your system installation
- To pre-download FFmpeg: `import clipflow; clipflow.setup_ffmpeg()`

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

[Unreleased]: https://github.com/ronaldgosso/clipflow/compare/v0.3.1...HEAD
[0.3.1]: https://github.com/ronaldgosso/clipflow/releases/tag/v0.3.1
[0.3.0]: https://github.com/ronaldgosso/clipflow/releases/tag/v0.3.0
[0.2.1]: https://github.com/ronaldgosso/clipflow/releases/tag/v0.2.1
[0.2.0]: https://github.com/ronaldgosso/clipflow/releases/tag/v0.2.0
[0.1.0]: https://github.com/ronaldgosso/clipflow/releases/tag/v0.1.0
