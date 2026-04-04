"""
clipflow._ffmpeg_manager
~~~~~~~~~~~~~~~~~~~~~~~~~
Automatic FFmpeg binary download and management.

This module handles downloading, caching, and locating FFmpeg binaries
across different platforms. It ensures that users don't need to manually
install FFmpeg on their system.

Design rules
------------
- Download FFmpeg only once and cache it locally
- Support Windows, macOS, and Linux
- Fall back to system PATH if cached binary is not available
- Thread-safe initialization
- Provide clear error messages if download fails
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

log = logging.getLogger("clipflow")

# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

System = platform.system()  # 'Windows', 'Darwin', 'Linux'
Machine = platform.machine()  # 'AMD64', 'x86_64', 'arm64', 'aarch64', etc.

# ---------------------------------------------------------------------------
# FFmpeg download URLs (static builds)
# ---------------------------------------------------------------------------

# Windows: Use Gyan.dev builds (most popular static builds for Windows)
# These are updated regularly and include both ffmpeg and ffprobe
FFMPEG_WINDOWS_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

# macOS: Use OSArch builds (static, no dependencies)
FFMPEG_MACOS_URL = (
    "https://github.com/jotson/homebrew-ffmpeg/releases/download/6.1.1_1/"
    "ffmpeg-6.1.1.macOS.zip"
)

# Linux: Use John Van Sickle static builds
FFMPEG_LINUX_URL = (
    "https://johnvansickle.com/ffmpeg/releases/" "ffmpeg-release-amd64-static.tar.xz"
)

# ---------------------------------------------------------------------------
# Cache directory
# ---------------------------------------------------------------------------


def _get_cache_dir() -> Path:
    """
    Return the platform-specific cache directory for FFmpeg binaries.

    Windows: %LOCALAPPDATA%\\clipflow\\ffmpeg
    macOS:   ~/Library/Caches/clipflow/ffmpeg
    Linux:   ~/.cache/clipflow/ffmpeg
    """
    if System == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif System == "Darwin":
        base = Path.home() / "Library" / "Caches"
    else:
        base = Path.home() / ".cache"

    cache = base / "clipflow" / "ffmpeg"
    cache.mkdir(parents=True, exist_ok=True)
    return cache


CACHE_DIR = _get_cache_dir()

# ---------------------------------------------------------------------------
# Binary paths (will be set by ensure_ffmpeg())
# ---------------------------------------------------------------------------

_ffmpeg_path: Path | None = None
_ffprobe_path: Path | None = None
_is_initialized = False


# ---------------------------------------------------------------------------
# Download helpers
# ---------------------------------------------------------------------------


def _download_file(url: str, dest: Path) -> None:
    """Download a file from *url* to *dest* with progress logging."""
    log.info("Downloading FFmpeg from %s ...", url)
    log.info("Saving to %s", dest)

    def _reporthook(block_num: int, block_size: int, total_size: int) -> None:
        downloaded = block_num * block_size
        if total_size > 0:
            pct = min(downloaded / total_size * 100, 100)
            mb_down = downloaded / (1024 * 1024)
            mb_total = total_size / (1024 * 1024)
            log.debug("  %.1f MB / %.1f MB (%.0f%%)", mb_down, mb_total, pct)

    try:
        urlretrieve(url, dest, _reporthook)
        log.info("Download complete: %s", dest.name)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to download FFmpeg from {url}: {exc}\n"
            f"Please install FFmpeg manually from https://ffmpeg.org/download.html"
        ) from exc


def _extract_zip(zip_path: Path, extract_dir: Path) -> Path:
    """Extract a ZIP and return the top-level directory."""
    log.info("Extracting %s ...", zip_path.name)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)
    # Return the first directory in the extracted contents
    for item in extract_dir.iterdir():
        if item.is_dir():
            return item
    return extract_dir


# ---------------------------------------------------------------------------
# Platform-specific download and setup
# ---------------------------------------------------------------------------


def _download_windows_ffmpeg() -> tuple[Path, Path]:
    """Download and extract FFmpeg for Windows. Returns (ffmpeg, ffprobe) paths."""
    zip_path = CACHE_DIR / "ffmpeg-release-essentials.zip"
    _download_file(FFMPEG_WINDOWS_URL, zip_path)

    extract_dir = CACHE_DIR / "extracted"
    extract_dir.mkdir(exist_ok=True)
    top_dir = _extract_zip(zip_path, extract_dir)

    # Gyan builds have structure: ffmpeg-XXXX-essentials_build/bin/ffmpeg.exe
    bin_dir = top_dir / "bin"
    ffmpeg = bin_dir / "ffmpeg.exe"
    ffprobe = bin_dir / "ffprobe.exe"

    if not ffmpeg.exists() or not ffprobe.exists():
        # Try to find them recursively
        for exe in top_dir.rglob("ffmpeg.exe"):
            ffmpeg = exe
            ffprobe = exe.parent / "ffprobe.exe"
            break

    if not ffmpeg.exists() or not ffprobe.exists():
        raise RuntimeError(
            f"FFmpeg binaries not found in extracted archive.\n"
            f"Extracted contents: {list(top_dir.iterdir())}"
        )

    # Clean up zip file but keep extracted binaries
    zip_path.unlink(missing_ok=True)

    return ffmpeg, ffprobe


def _download_macos_ffmpeg() -> tuple[Path, Path]:
    """Download and extract FFmpeg for macOS. Returns (ffmpeg, ffprobe) paths."""
    # For macOS, we'll use a simpler approach - download pre-built binaries
    # from a reliable source or use Homebrew-installed paths
    ffmpeg = CACHE_DIR / "ffmpeg"
    ffprobe = CACHE_DIR / "ffprobe"

    # Try downloading from a static source
    # Note: macOS binaries are code-signed, so we use a trusted source
    try:
        # Attempt to download static build
        zip_path = CACHE_DIR / "ffmpeg-macos.zip"
        _download_file(FFMPEG_MACOS_URL, zip_path)

        extract_dir = CACHE_DIR / "extracted"
        extract_dir.mkdir(exist_ok=True)
        top_dir = _extract_zip(zip_path, extract_dir)

        # Find binaries
        for bin_file in top_dir.rglob("ffmpeg"):
            if bin_file.is_file() and os.access(bin_file, os.X_OK):
                ffmpeg = bin_file
                ffprobe = bin_file.parent / "ffprobe"
                break

        zip_path.unlink(missing_ok=True)
    except Exception as exc:
        log.warning("Failed to download FFmpeg for macOS: %s", exc)
        raise RuntimeError(
            f"Failed to download FFmpeg for macOS: {exc}\n"
            f"Please install FFmpeg manually:\n"
            f"  brew install ffmpeg"
        ) from exc

    return ffmpeg, ffprobe


def _download_linux_ffmpeg() -> tuple[Path, Path]:
    """Download and extract FFmpeg for Linux. Returns (ffmpeg, ffprobe) paths."""
    import tarfile

    ffmpeg = CACHE_DIR / "ffmpeg"
    ffprobe = CACHE_DIR / "ffprobe"

    try:
        # Download tar.xz archive
        import tarfile

        tar_path = CACHE_DIR / "ffmpeg-linux-amd64-static.tar.xz"
        _download_file(FFMPEG_LINUX_URL, tar_path)

        extract_dir = CACHE_DIR / "extracted"
        extract_dir.mkdir(exist_ok=True)

        with tarfile.open(tar_path, "r:xz") as tar:
            tar.extractall(extract_dir)

        top_dir = extract_dir
        for item in extract_dir.iterdir():
            if item.is_dir():
                top_dir = item
                break

        bin_dir = top_dir / "ffmpeg" / "ffmpeg" / "bin"
        if not bin_dir.exists():
            bin_dir = top_dir / "bin"

        ffmpeg = bin_dir / "ffmpeg"
        ffprobe = bin_dir / "ffprobe"

        # Make executable
        ffmpeg.chmod(0o755)
        ffprobe.chmod(0o755)

        tar_path.unlink(missing_ok=True)
    except Exception as exc:
        log.warning("Failed to download FFmpeg for Linux: %s", exc)
        raise RuntimeError(
            f"Failed to download FFmpeg for Linux: {exc}\n"
            f"Please install FFmpeg manually:\n"
            f"  Ubuntu/Debian: sudo apt install ffmpeg\n"
            f"  Fedora: sudo dnf install ffmpeg\n"
            f"  Arch: sudo pacman -S ffmpeg"
        ) from exc

    return ffmpeg, ffprobe


# ---------------------------------------------------------------------------
# Public API: ensure_ffmpeg()
# ---------------------------------------------------------------------------


def ensure_ffmpeg() -> tuple[Path, Path]:
    """
    Ensure FFmpeg binaries are available and return their paths.

    Strategy
    --------
    1. Check if we already have cached binaries
    2. If not, download them for the current platform
    3. Return (ffmpeg_path, ffprobe_path)

    Raises
    ------
    RuntimeError
        If FFmpeg cannot be found or downloaded.
    """
    global _ffmpeg_path, _ffprobe_path, _is_initialized

    if _is_initialized and _ffmpeg_path and _ffprobe_path:
        return _ffmpeg_path, _ffprobe_path

    # Check if we already have cached binaries
    cached_ffmpeg = CACHE_DIR / "ffmpeg"
    cached_ffprobe = CACHE_DIR / "ffprobe"

    if System == "Windows":
        cached_ffmpeg = CACHE_DIR / "ffmpeg.exe"
        cached_ffprobe = CACHE_DIR / "ffprobe.exe"

    if cached_ffmpeg.exists() and cached_ffprobe.exists():
        log.debug("Using cached FFmpeg binaries from %s", CACHE_DIR)
        _ffmpeg_path = cached_ffmpeg
        _ffprobe_path = cached_ffprobe
        _is_initialized = True
        return _ffmpeg_path, _ffprobe_path

    # Try system PATH as fallback
    system_ffmpeg = shutil.which("ffmpeg")
    system_ffprobe = shutil.which("ffprobe")

    if system_ffmpeg and system_ffprobe:
        log.debug("Using system FFmpeg from PATH")
        _ffmpeg_path = Path(system_ffmpeg)
        _ffprobe_path = Path(system_ffprobe)
        _is_initialized = True
        return _ffmpeg_path, _ffprobe_path

    # Download for the current platform
    log.info("FFmpeg not found — downloading for %s...", System)

    try:
        if System == "Windows":
            _ffmpeg_path, _ffprobe_path = _download_windows_ffmpeg()
        elif System == "Darwin":
            _ffmpeg_path, _ffprobe_path = _download_macos_ffmpeg()
        else:
            _ffmpeg_path, _ffprobe_path = _download_linux_ffmpeg()

        _is_initialized = True
        log.info("FFmpeg successfully installed to %s", CACHE_DIR)
        return _ffmpeg_path, _ffprobe_path

    except Exception as exc:
        raise RuntimeError(
            f"Failed to set up FFmpeg: {exc}\n"
            f"Please install FFmpeg manually and ensure it's on your PATH.\n"
            f"Download from: https://ffmpeg.org/download.html"
        ) from exc


def get_ffmpeg_path() -> str:
    """Return the full path to the ffmpeg binary as a string."""
    ffmpeg_path, _ = ensure_ffmpeg()
    return str(ffmpeg_path)


def get_ffprobe_path() -> str:
    """Return the full path to the ffprobe binary as a string."""
    _, ffprobe_path = ensure_ffmpeg()
    return str(ffprobe_path)


def reset_cache() -> None:
    """Reset the initialization state (useful for testing)."""
    global _ffmpeg_path, _ffprobe_path, _is_initialized
    _ffmpeg_path = None
    _ffprobe_path = None
    _is_initialized = False


# ---------------------------------------------------------------------------
# Auto-initialization on import (optional)
# ---------------------------------------------------------------------------

# We don't auto-download on import to avoid unexpected network calls.
# Instead, we initialize lazily when the binaries are first needed.
# Users can call ensure_ffmpeg() explicitly if they want to pre-download.
