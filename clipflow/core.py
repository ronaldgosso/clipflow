"""
clipflow.core
~~~~~~~~~~~~~
The public API.  Import from ``clipflow`` directly — not from here.

Three entry points
------------------
``trim(input_path, clips, output_dir)``
    Process one or more :class:`~clipflow.models.ClipSpec` from a
    single video file.  Returns a list of :class:`~clipflow.models.ClipResult`.

``inspect(input_path)``
    Return a :class:`~clipflow.models.VideoInfo` for any video file.

``batch(specs)``
    Process multiple :class:`~clipflow.models.BatchSpec` objects,
    each potentially from a different source file.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Callable

from clipflow._ffmpeg import (
    build_aspect_ratio_filter,
    copy_file,
    probe,
    run_trim,
)
from clipflow.models import (
    BatchSpec,
    ClipResult,
    ClipSpec,
    VideoInfo,
)

log = logging.getLogger("clipflow")

# Type alias for the optional progress callback
ProgressCallback = Callable[[int, int, ClipResult], None]


# ---------------------------------------------------------------------------
# inspect
# ---------------------------------------------------------------------------

def inspect(input_path: str | Path) -> VideoInfo:
    """
    Return metadata about *input_path* without modifying it.

    Parameters
    ----------
    input_path:
        Path to a video file (mp4, mkv, avi, mov, …).

    Returns
    -------
    :class:`~clipflow.models.VideoInfo`

    Raises
    ------
    FileNotFoundError
        If *input_path* does not exist.
    RuntimeError
        If ffprobe is not on PATH.

    Examples
    --------
    >>> import clipflow
    >>> info = clipflow.inspect("lecture.mp4")
    >>> print(info.duration_fmt, info.resolution)
    01:23:45 1920×1080
    """
    p = Path(input_path)
    if not p.exists():
        raise FileNotFoundError(f"No such file: {p}")

    raw = probe(p)

    fmt = raw.get("format", {})
    duration_s = float(fmt.get("duration", 0))
    size_bytes = int(fmt.get("size", p.stat().st_size))

    video_codec: str = "unknown"
    audio_codec: str | None = None
    width = height = 0
    fps = 0.0

    for stream in raw.get("streams", []):
        if stream.get("codec_type") == "video" and video_codec == "unknown":
            video_codec = stream.get("codec_name", "unknown")
            width = int(stream.get("width", 0))
            height = int(stream.get("height", 0))
            # r_frame_rate is "num/den" e.g. "30000/1001"
            r = stream.get("r_frame_rate", "0/1")
            num, den = (int(x) for x in r.split("/"))
            fps = num / den if den else 0.0
        elif stream.get("codec_type") == "audio" and audio_codec is None:
            audio_codec = stream.get("codec_name")

    return VideoInfo(
        path=p.resolve(),
        duration_s=duration_s,
        width=width,
        height=height,
        fps=fps,
        video_codec=video_codec,
        audio_codec=audio_codec,
        size_bytes=size_bytes,
    )


# ---------------------------------------------------------------------------
# trim — single-file, one or many clips
# ---------------------------------------------------------------------------

def trim(
    input_path: str | Path,
    clips: ClipSpec | list[ClipSpec],
    *,
    output_dir: str | Path = "output",
    on_progress: ProgressCallback | None = None,
) -> list[ClipResult]:
    """
    Trim one or more segments from *input_path*.

    Parameters
    ----------
    input_path:
        Source video file.
    clips:
        A single :class:`~clipflow.models.ClipSpec` or a list of them.
    output_dir:
        Directory where trimmed clips are written.
        Created automatically if it does not exist.
        Highlights are written to ``<output_dir>/highlights/``.
    on_progress:
        Optional callable ``(index, total, result) -> None``
        called after each clip finishes processing.

    Returns
    -------
    list[:class:`~clipflow.models.ClipResult`]
        One result per clip, in order. Check ``result.ok`` and
        ``result.error`` for per-clip status.

    Examples
    --------
    Stream-copy (fastest, lossless)::

        import clipflow
        from clipflow import ClipSpec, parse_range

        results = clipflow.trim(
            "documentary.mp4",
            ClipSpec(parse_range("00:30", "02:15")),
        )

    With compression and a highlight::

        from clipflow import ClipSpec, parse_range, COMPRESS_HIGH, AR_9_16

        clips = [
            ClipSpec(parse_range("00:00", "01:00"), label="intro"),
            ClipSpec(
                parse_range("05:00", "06:30"),
                highlight=True,
                compress=COMPRESS_HIGH,
                aspect_ratio=AR_9_16,
                label="best_moment",
            ),
        ]
        results = clipflow.trim("video.mp4", clips, output_dir="out")
    """
    src = Path(input_path)
    if not src.exists():
        raise FileNotFoundError(f"No such file: {src}")

    out_dir = Path(output_dir)
    highlight_dir = out_dir / "highlights"

    if isinstance(clips, ClipSpec):
        clips = [clips]

    suffix = src.suffix  # keep same container format
    results: list[ClipResult] = []

    for idx, spec in enumerate(clips):
        label = spec.effective_label()
        out_path = out_dir / f"{label}{suffix}"
        t0 = time.perf_counter()

        try:
            aspect_filter: str | None = None
            if spec.aspect_ratio is not None:
                aspect_filter = build_aspect_ratio_filter(
                    spec.aspect_ratio.width,
                    spec.aspect_ratio.height,
                )

            if spec.compress is not None:
                run_trim(
                    src,
                    out_path,
                    start=spec.time_range.start,
                    duration=spec.time_range.duration,
                    aspect_ratio_filter=aspect_filter,
                    crf=spec.compress.crf,
                    preset=spec.compress.preset,
                    codec=spec.compress.codec,
                    audio_bitrate=spec.compress.audio_bitrate,
                )
            else:
                run_trim(
                    src,
                    out_path,
                    start=spec.time_range.start,
                    duration=spec.time_range.duration,
                    aspect_ratio_filter=aspect_filter,
                )

            # ---------- highlight copy ----------
            hl_path: Path | None = None
            if spec.highlight:
                hl_path = highlight_dir / f"{label}{suffix}"
                copy_file(out_path, hl_path)
                log.info("Highlight saved → %s", hl_path)

            elapsed = time.perf_counter() - t0
            result = ClipResult(
                spec=spec,
                output_path=out_path.resolve(),
                highlight_path=hl_path.resolve() if hl_path else None,
                duration_s=elapsed,
                ok=True,
            )
            log.info(
                "[%d/%d] ✓ %s (%.2fs)", idx + 1, len(clips), label, elapsed
            )

        except Exception as exc:
            elapsed = time.perf_counter() - t0
            result = ClipResult(
                spec=spec,
                output_path=None,
                highlight_path=None,
                duration_s=elapsed,
                ok=False,
                error=str(exc),
            )
            log.error("[%d/%d] ✗ %s — %s", idx + 1, len(clips), label, exc)

        results.append(result)
        if on_progress:
            on_progress(idx + 1, len(clips), result)

    return results


# ---------------------------------------------------------------------------
# batch — multiple source files
# ---------------------------------------------------------------------------

def batch(
    specs: list[BatchSpec],
    *,
    on_progress: ProgressCallback | None = None,
) -> dict[Path, list[ClipResult]]:
    """
    Process multiple :class:`~clipflow.models.BatchSpec` objects.

    Parameters
    ----------
    specs:
        Each :class:`~clipflow.models.BatchSpec` targets one input file
        and carries its own list of clips and output directory.
    on_progress:
        Same signature as in :func:`trim` — called per clip across
        all batch specs.

    Returns
    -------
    dict[Path, list[:class:`~clipflow.models.ClipResult`]]
        Keyed by the resolved input path of each spec.

    Examples
    --------
    ::

        import clipflow
        from clipflow import BatchSpec, ClipSpec, parse_range

        specs = [
            BatchSpec(
                input_path=Path("ep01.mp4"),
                clips=[ClipSpec(parse_range("00:30", "01:30"), label="cold_open")],
                output_dir=Path("ep01_clips"),
            ),
            BatchSpec(
                input_path=Path("ep02.mp4"),
                clips=[ClipSpec(parse_range("00:00", "02:00"))],
                output_dir=Path("ep02_clips"),
            ),
        ]
        all_results = clipflow.batch(specs)
    """
    all_results: dict[Path, list[ClipResult]] = {}

    for batch_spec in specs:
        src = Path(batch_spec.input_path).resolve()
        results = trim(
            batch_spec.input_path,
            batch_spec.clips,
            output_dir=batch_spec.output_dir,
            on_progress=on_progress,
        )
        all_results[src] = results

    return all_results
