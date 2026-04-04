"""
clipflow.models
~~~~~~~~~~~~~~~
All typed dataclasses that form the public API contract.
Nothing in here touches subprocess or the filesystem.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Time range
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TimeRange:
    """
    A half-open interval [start, end) expressed in seconds.

    Construct via :func:`clipflow.parse_time` or directly::

        TimeRange(start=60.0, end=90.0)
    """

    start: float  # seconds
    end: float    # seconds

    def __post_init__(self) -> None:
        if self.start < 0:
            raise ValueError(f"start must be >= 0, got {self.start}")
        if self.end <= self.start:
            raise ValueError(
                f"end ({self.end}) must be greater than start ({self.start})"
            )

    @property
    def duration(self) -> float:
        return self.end - self.start

    def __repr__(self) -> str:
        return f"TimeRange({_fmt(self.start)} → {_fmt(self.end)})"


def _fmt(seconds: float) -> str:
    """Format seconds as MM:SS.mmm for display."""
    m, s = divmod(seconds, 60)
    return f"{int(m):02d}:{s:06.3f}"


# ---------------------------------------------------------------------------
# Compression
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CompressOptions:
    """
    Optional compression settings applied after trimming.

    Parameters
    ----------
    crf:
        Constant Rate Factor (0 = lossless, 51 = worst).
        18–28 is the practical range; 23 is ffmpeg's default.
    preset:
        ffmpeg encoding speed preset. Slower = smaller file.
        Choices: ultrafast, superfast, veryfast, faster, fast,
                 medium, slow, slower, veryslow.
    codec:
        Video codec. ``libx264`` (H.264) is widest-compatible.
        Use ``libx265`` for smaller files at the cost of encode time.
    audio_bitrate:
        Audio bitrate string, e.g. ``"128k"``, ``"192k"``.
        ``None`` copies the audio stream unchanged.
    """

    crf: int = 23
    preset: str = "medium"
    codec: str = "libx264"
    audio_bitrate: str | None = None

    def __post_init__(self) -> None:
        if not (0 <= self.crf <= 51):
            raise ValueError(f"crf must be 0–51, got {self.crf}")
        valid_presets = {
            "ultrafast", "superfast", "veryfast", "faster",
            "fast", "medium", "slow", "slower", "veryslow",
        }
        if self.preset not in valid_presets:
            raise ValueError(
                f"preset must be one of {sorted(valid_presets)}, got {self.preset!r}"
            )


# Convenient named presets
COMPRESS_LOW = CompressOptions(crf=28, preset="fast")
COMPRESS_MEDIUM = CompressOptions(crf=23, preset="medium")
COMPRESS_HIGH = CompressOptions(crf=18, preset="slow")


# ---------------------------------------------------------------------------
# Aspect ratio
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AspectRatio:
    """
    Target aspect ratio applied via crop-then-pad.

    Common shortcuts are available as module-level constants:
    ``AR_16_9``, ``AR_9_16``, ``AR_1_1``, ``AR_4_3``.
    """

    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("width and height must be positive integers")

    @property
    def ratio(self) -> float:
        return self.width / self.height

    def __repr__(self) -> str:
        return f"AspectRatio({self.width}:{self.height})"


AR_16_9 = AspectRatio(16, 9)
AR_9_16 = AspectRatio(9, 16)
AR_1_1 = AspectRatio(1, 1)
AR_4_3 = AspectRatio(4, 3)


# ---------------------------------------------------------------------------
# Clip spec — the main unit of work
# ---------------------------------------------------------------------------

@dataclass
class ClipSpec:
    """
    Everything clipflow needs to know to produce one output clip.

    Parameters
    ----------
    time_range:
        The segment to extract, as a :class:`TimeRange`.
    highlight:
        If ``True`` this clip is also written to the ``highlights/``
        subfolder of the output directory, separately from normal clips.
    compress:
        Optional :class:`CompressOptions`. ``None`` = stream-copy
        (lossless, fast). Pass a ``CompressOptions`` instance to
        re-encode with compression.
    aspect_ratio:
        Optional :class:`AspectRatio`. Applied after trim/compress.
    label:
        Human-readable name for this clip, used in filenames and logs.
        Defaults to the time range string.
    """

    time_range: TimeRange
    highlight: bool = False
    compress: CompressOptions | None = None
    aspect_ratio: AspectRatio | None = None
    label: str | None = None

    def effective_label(self) -> str:
        if self.label:
            return self.label
        start = int(self.time_range.start)
        end = int(self.time_range.end)
        return f"clip_{start:04d}s_{end:04d}s"


# ---------------------------------------------------------------------------
# Result — returned after every operation
# ---------------------------------------------------------------------------

@dataclass
class ClipResult:
    """
    The outcome of processing one :class:`ClipSpec`.

    Attributes
    ----------
    spec:
        The :class:`ClipSpec` that was processed.
    output_path:
        Absolute path to the produced file.
    highlight_path:
        Absolute path to the highlight copy, or ``None``.
    duration_s:
        Wall-clock seconds the ffmpeg call took.
    ok:
        ``True`` if the clip was produced without error.
    error:
        Error message if ``ok`` is ``False``, else ``None``.
    """

    spec: ClipSpec
    output_path: Path | None
    highlight_path: Path | None
    duration_s: float
    ok: bool
    error: str | None = None

    def __repr__(self) -> str:
        status = "✓" if self.ok else "✗"
        return (
            f"ClipResult({status} {self.spec.effective_label()!r} "
            f"→ {self.output_path} [{self.duration_s:.2f}s])"
        )


# ---------------------------------------------------------------------------
# VideoInfo — returned by inspect()
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class VideoInfo:
    """
    Metadata about a video file, populated by :func:`clipflow.inspect`.

    All fields are read-only.
    """

    path: Path
    duration_s: float
    width: int
    height: int
    fps: float
    video_codec: str
    audio_codec: str | None
    size_bytes: int

    @property
    def duration_fmt(self) -> str:
        h, rem = divmod(int(self.duration_s), 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    @property
    def size_mb(self) -> float:
        return round(self.size_bytes / 1_048_576, 2)

    @property
    def resolution(self) -> str:
        return f"{self.width}×{self.height}"

    def __repr__(self) -> str:
        return (
            f"VideoInfo({self.path.name!r} "
            f"{self.resolution} {self.fps:.2f}fps "
            f"{self.duration_fmt} {self.size_mb}MB)"
        )


# ---------------------------------------------------------------------------
# Batch spec
# ---------------------------------------------------------------------------

@dataclass
class BatchSpec:
    """
    A collection of clips to cut from a single input file.

    Parameters
    ----------
    input_path:
        Source video file.
    clips:
        List of :class:`ClipSpec` instances to extract.
    output_dir:
        Destination directory. Created if it does not exist.
    """

    input_path: Path
    clips: list[ClipSpec] = field(default_factory=list)
    output_dir: Path = field(default_factory=lambda: Path("output"))

    def add(self, spec: ClipSpec) -> BatchSpec:
        """Fluent helper — add a clip and return self."""
        self.clips.append(spec)
        return self
