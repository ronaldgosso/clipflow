"""
clipflow._ffmpeg
~~~~~~~~~~~~~~~~
Low-level ffmpeg/ffprobe subprocess wrappers.

This is the ONLY module that touches subprocess.
Every public function returns plain Python types;
no dataclasses from models are imported here to keep
the dependency graph clean.

Design rules
------------
- Build the command as a list[str], log it at DEBUG, run it.
- Capture stderr; surface it only on non-zero exit.
- Never swallow CalledProcessError — let callers decide.
- Use bundled/downloaded FFmpeg binaries via _ffmpeg_manager.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path

from clipflow._ffmpeg_manager import ensure_ffmpeg

log = logging.getLogger("clipflow")


# ---------------------------------------------------------------------------
# ffmpeg / ffprobe availability check
# ---------------------------------------------------------------------------


def require_ffmpeg() -> None:
    """Raise :class:`RuntimeError` if ffmpeg is not available."""
    try:
        ffmpeg_path, _ = ensure_ffmpeg()
        if not ffmpeg_path.exists():
            raise RuntimeError(
                f"FFmpeg binary not found at: {ffmpeg_path}\n"
                "Try reinstalling clipflow or install FFmpeg manually from "
                "https://ffmpeg.org/download.html"
            )
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(
            f"FFmpeg not found: {exc}\n"
            "Install it from https://ffmpeg.org/download.html "
            "and ensure it is accessible from your terminal."
        ) from exc


def require_ffprobe() -> None:
    """Raise :class:`RuntimeError` if ffprobe is not available."""
    try:
        _, ffprobe_path = ensure_ffmpeg()
        if not ffprobe_path.exists():
            raise RuntimeError(
                f"FFprobe binary not found at: {ffprobe_path}\n"
                "Try reinstalling clipflow or install FFmpeg manually from "
                "https://ffmpeg.org/download.html"
            )
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(
            f"FFprobe not found: {exc}\n"
            "It ships alongside ffmpeg — ensure the full ffmpeg build is installed."
        ) from exc


# ---------------------------------------------------------------------------
# Core trim command builder
# ---------------------------------------------------------------------------


def _build_trim_command(
    input_path: Path,
    output_path: Path,
    start: float,
    duration: float,
    *,
    crf: int | None = None,
    preset: str | None = None,
    codec: str | None = None,
    audio_bitrate: str | None = None,
    aspect_ratio_filter: str | None = None,
) -> list[str]:
    """
    Return the ffmpeg command list for a single trim operation.

    Stream-copy mode (fast, lossless)
    ----------------------------------
    When crf/preset/codec are all None we copy both streams without
    re-encoding: ``-c copy``. The seek is placed BEFORE -i so that
    ffmpeg uses a fast keyframe seek rather than a slow linear decode.

    Compress mode
    -------------
    When crf/preset/codec are provided we re-encode. The seek must
    then be placed AFTER -i (input seek breaks filter chains).

    The distinction is handled automatically here.
    """
    compress = crf is not None

    # Get the actual ffmpeg binary path
    ffmpeg_path, _ = ensure_ffmpeg()

    cmd: list[str] = [str(ffmpeg_path), "-y"]  # -y overwrites output without prompt

    if not compress:
        # Fast seek BEFORE input — only safe for stream-copy
        cmd += ["-ss", str(start), "-t", str(duration)]

    cmd += ["-i", str(input_path)]

    if compress:
        # Accurate seek AFTER input — required for re-encoding
        cmd += ["-ss", str(start), "-t", str(duration)]

    # ---------- video filters ----------
    vf_parts: list[str] = []
    if aspect_ratio_filter:
        vf_parts.append(aspect_ratio_filter)

    if vf_parts:
        cmd += ["-vf", ",".join(vf_parts)]

    # ---------- codec / quality ----------
    if compress:
        cmd += [
            "-c:v",
            codec or "libx264",
            "-crf",
            str(crf),
            "-preset",
            preset or "medium",
        ]
        if audio_bitrate:
            cmd += ["-b:a", audio_bitrate]
        else:
            cmd += ["-c:a", "copy"]
    else:
        if aspect_ratio_filter:
            # Can't stream-copy with a video filter — must re-encode video
            cmd += ["-c:v", "libx264", "-crf", "18", "-c:a", "copy"]
        else:
            cmd += ["-c", "copy"]

    cmd.append(str(output_path))
    return cmd


# ---------------------------------------------------------------------------
# Aspect ratio filter builder
# ---------------------------------------------------------------------------


def build_aspect_ratio_filter(target_w: int, target_h: int) -> str:
    """
    Build an ffmpeg ``-vf`` expression that crops to *target_w*:*target_h*.

    Strategy: crop the input to the target ratio without upscaling,
    then (if needed) pad to exact dimensions that are multiples of 2.

    The ``iw`` / ``ih`` ffmpeg variables refer to the input width/height,
    so the filter adapts to any source resolution.
    """
    # Crop to target ratio
    # crop=w:h:x:y — we centre the crop
    crop = (
        f"crop="
        f"if(gt(iw/ih\\,{target_w}/{target_h})\\,"
        f"ih*{target_w}/{target_h}\\,iw):"
        f"if(gt(iw/ih\\,{target_w}/{target_h})\\,"
        f"ih\\,iw*{target_h}/{target_w}):"
        f"(iw-min(iw\\,ih*{target_w}/{target_h}))/2:"
        f"(ih-min(ih\\,iw*{target_h}/{target_w}))/2"
    )
    # Ensure dimensions are even (required by most codecs)
    scale = "scale=trunc(iw/2)*2:trunc(ih/2)*2"
    return f"{crop},{scale}"


# ---------------------------------------------------------------------------
# ffprobe metadata extractor
# ---------------------------------------------------------------------------


def probe(input_path: Path) -> dict:  # type: ignore[type-arg]
    """
    Run ffprobe and return the raw JSON dict.

    Returns
    -------
    dict
        Parsed JSON output with ``format`` and ``streams`` keys.
    """
    require_ffprobe()
    _, ffprobe_path = ensure_ffmpeg()
    cmd = [
        str(ffprobe_path),
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(input_path),
    ]
    log.debug("ffprobe cmd: %s", " ".join(cmd))
    result = subprocess.run(
        cmd,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# Primary trim executor
# ---------------------------------------------------------------------------


def run_trim(
    input_path: Path,
    output_path: Path,
    start: float,
    duration: float,
    *,
    crf: int | None = None,
    preset: str | None = None,
    codec: str | None = None,
    audio_bitrate: str | None = None,
    aspect_ratio_filter: str | None = None,
) -> None:
    """
    Execute the ffmpeg trim command.

    Raises
    ------
    subprocess.CalledProcessError
        On non-zero ffmpeg exit. The ``stderr`` attribute contains
        the full ffmpeg diagnostic output.
    RuntimeError
        If ffmpeg is not found on PATH.
    """
    require_ffmpeg()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = _build_trim_command(
        input_path,
        output_path,
        start,
        duration,
        crf=crf,
        preset=preset,
        codec=codec,
        audio_bitrate=audio_bitrate,
        aspect_ratio_filter=aspect_ratio_filter,
    )

    log.debug("ffmpeg cmd: %s", " ".join(cmd))

    subprocess.run(
        cmd,
        check=True,
        capture_output=True,  # capture stdout+stderr; surfaces on error
    )


# ---------------------------------------------------------------------------
# File copy (for highlight duplication)
# ---------------------------------------------------------------------------


def copy_file(src: Path, dst: Path) -> None:
    """Copy *src* to *dst*, creating parent directories as needed."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
