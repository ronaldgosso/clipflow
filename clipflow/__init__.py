"""
clipflow
~~~~~~~~
Trim, compress, and highlight video clips — powered by ffmpeg subprocess.

FFmpeg binaries are automatically downloaded and managed by clipflow.
On first use, clipflow will download FFmpeg if not found in the cache
or system PATH. You can also pre-download FFmpeg explicitly::

    >>> import clipflow
    >>> clipflow.setup_ffmpeg()  # Optional: pre-download FFmpeg
    >>> ffmpeg_path, ffprobe_path = clipflow.get_ffmpeg_paths()

Quick start
-----------
>>> import clipflow
>>> results = clipflow.trim(
...     "documentary.mp4",
...     clipflow.ClipSpec(clipflow.parse_range("01:00", "02:30")),
... )
>>> results[0].ok
True
"""

from clipflow._ffmpeg_manager import (
    ensure_ffmpeg as setup_ffmpeg,
    get_ffmpeg_path,
    get_ffprobe_path,
)
from clipflow.core import batch, inspect, trim
from clipflow.models import (
    AR_1_1,
    AR_4_3,
    AR_9_16,
    AR_16_9,
    COMPRESS_HIGH,
    COMPRESS_LOW,
    COMPRESS_MEDIUM,
    AspectRatio,
    BatchSpec,
    ClipResult,
    ClipSpec,
    CompressOptions,
    TimeRange,
    VideoInfo,
)
from clipflow.parser import parse_range, parse_seconds

__all__ = [
    # functions
    "trim",
    "inspect",
    "batch",
    "parse_range",
    "parse_seconds",
    "setup_ffmpeg",
    "get_ffmpeg_path",
    "get_ffprobe_path",
    # core models
    "ClipSpec",
    "TimeRange",
    "ClipResult",
    "VideoInfo",
    "BatchSpec",
    # compression
    "CompressOptions",
    "COMPRESS_LOW",
    "COMPRESS_MEDIUM",
    "COMPRESS_HIGH",
    # aspect ratio
    "AspectRatio",
    "AR_16_9",
    "AR_9_16",
    "AR_1_1",
    "AR_4_3",
]

__version__ = "0.1.0"
__author__ = "Ronald Isack Gosso"
