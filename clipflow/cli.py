"""
clipflow.cli
~~~~~~~~~~~~
Command-line interface for clipflow.

Commands
--------
``clipflow trim``    — trim one or more segments from a video
``clipflow inspect`` — print metadata about a video file
``clipflow batch``   — process multiple clips from a JSON spec file

All output is written to stdout/stderr.  Uses only stdlib (argparse,
json, textwrap) — no Click, no Rich.  Terminal colours are detected
via ``sys.stdout.isatty()`` and toggled off when piped.
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
import time
from pathlib import Path

import clipflow
from clipflow.models import (
    AR_1_1,
    AR_4_3,
    AR_9_16,
    AR_16_9,
    AspectRatio,
    BatchSpec,
    ClipResult,
    ClipSpec,
    CompressOptions,
)
from clipflow.parser import parse_range

# ---------------------------------------------------------------------------
# Terminal colour helpers (pure ANSI, no deps)
# ---------------------------------------------------------------------------

_USE_COLOUR = sys.stdout.isatty()

_C = {
    "reset":  "\033[0m",
    "bold":   "\033[1m",
    "dim":    "\033[2m",
    "green":  "\033[32m",
    "yellow": "\033[33m",
    "cyan":   "\033[36m",
    "red":    "\033[31m",
    "white":  "\033[97m",
    "grey":   "\033[90m",
}


def _c(code: str, text: str) -> str:
    if not _USE_COLOUR:
        return text
    return f"{_C[code]}{text}{_C['reset']}"


def _bold(t: str) -> str:   return _c("bold",   t)
def _green(t: str) -> str:  return _c("green",  t)
def _yellow(t: str) -> str: return _c("yellow", t)
def _cyan(t: str) -> str:   return _c("cyan",   t)
def _red(t: str) -> str:    return _c("red",    t)
def _grey(t: str) -> str:   return _c("grey",   t)
def _dim(t: str) -> str:    return _c("dim",    t)


# ---------------------------------------------------------------------------
# Print helpers
# ---------------------------------------------------------------------------

def _banner() -> None:
    """Print the clipflow wordmark."""
    print(_bold(_cyan("clipflow")) + _dim(f" v{clipflow.__version__}"))
    print()


def _rule(width: int = 56) -> None:
    print(_grey("─" * width))


def _ok(msg: str) -> None:
    print(_green("  ✓ ") + msg)


def _err(msg: str) -> None:
    print(_red("  ✗ ") + msg, file=sys.stderr)


def _info(label: str, value: str) -> None:
    print(f"  {_dim(label + ':')}  {value}")


def _print_result(idx: int, total: int, result: ClipResult) -> None:
    label = result.spec.effective_label()
    elapsed = f"{result.duration_s:.2f}s"
    prefix = _grey(f"[{idx}/{total}]")

    if result.ok:
        path_str = str(result.output_path)
        print(f"{prefix} {_green('✓')} {_bold(label)}  {_grey(elapsed)}")
        print(f"       {_dim('→')} {path_str}")
        if result.highlight_path:
            print(f"       {_dim('★')} {_yellow('highlight')} → {result.highlight_path}")
    else:
        print(f"{prefix} {_red('✗')} {_bold(label)}  {_grey(elapsed)}")
        print(f"       {_red('error:')} {result.error}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Shared arg parsers
# ---------------------------------------------------------------------------

def _add_compress_args(p: argparse.ArgumentParser) -> None:
    g = p.add_argument_group("compression (optional — omit for lossless stream-copy)")
    g.add_argument(
        "--compress",
        choices=["low", "medium", "high"],
        metavar="PRESET",
        help="Enable re-encoding: low | medium | high  (maps to CRF 28/23/18)",
    )
    g.add_argument(
        "--crf",
        type=int,
        metavar="N",
        help="Custom CRF value 0–51 (overrides --compress preset quality)",
    )
    g.add_argument(
        "--codec",
        default="libx264",
        metavar="CODEC",
        help="Video codec  [default: libx264]",
    )
    g.add_argument(
        "--audio-bitrate",
        metavar="RATE",
        help="Audio bitrate e.g. 128k, 192k  [default: copy stream]",
    )


def _add_aspect_args(p: argparse.ArgumentParser) -> None:
    g = p.add_argument_group("aspect ratio (optional)")
    g.add_argument(
        "--aspect",
        metavar="RATIO",
        help=(
            "Crop/pad to target ratio. "
            "Named shortcuts: 16:9, 9:16, 1:1, 4:3. "
            "Or any W:H e.g. 21:9"
        ),
    )


_NAMED_RATIOS = {
    "16:9": AR_16_9,
    "9:16": AR_9_16,
    "1:1":  AR_1_1,
    "4:3":  AR_4_3,
}


def _parse_aspect(value: str | None) -> AspectRatio | None:
    if value is None:
        return None
    if value in _NAMED_RATIOS:
        return _NAMED_RATIOS[value]
    try:
        w_str, h_str = value.split(":")
        return AspectRatio(int(w_str), int(h_str))
    except (ValueError, TypeError):
        raise argparse.ArgumentTypeError(
            f"Invalid aspect ratio {value!r}. Use W:H format e.g. 16:9"
        ) from None


def _build_compress(
    compress: str | None,
    crf: int | None,
    codec: str,
    audio_bitrate: str | None,
) -> CompressOptions | None:
    """Build a CompressOptions from CLI args, or return None for stream-copy."""
    if compress is None and crf is None:
        return None

    # Named preset sets base CRF + speed preset
    preset_map = {
        "low":    clipflow.COMPRESS_LOW,
        "medium": clipflow.COMPRESS_MEDIUM,
        "high":   clipflow.COMPRESS_HIGH,
    }

    if compress is not None:
        base = preset_map[compress]
        return CompressOptions(
            crf=crf if crf is not None else base.crf,
            preset=base.preset,
            codec=codec,
            audio_bitrate=audio_bitrate,
        )

    # --crf supplied without --compress → medium speed
    return CompressOptions(
        crf=crf,  # type: ignore[arg-type]  # crf is not None here
        preset="medium",
        codec=codec,
        audio_bitrate=audio_bitrate,
    )


# ---------------------------------------------------------------------------
# `clipflow trim`
# ---------------------------------------------------------------------------

def _cmd_trim(args: argparse.Namespace) -> int:
    """
    clipflow trim input.mp4 00:00-01:30 [05:00-06:00 ...] [options]

    Each range is  START-END  where START and END accept:
        MM:SS       01:30
        HH:MM:SS    01:02:03
        plain secs  90
    """
    _banner()

    input_path = Path(args.input)
    if not input_path.exists():
        _err(f"File not found: {input_path}")
        return 1

    # Parse ranges
    clips: list[ClipSpec] = []
    compress = _build_compress(
        args.compress, args.crf, args.codec, args.audio_bitrate
    )
    aspect = _parse_aspect(getattr(args, "aspect", None))

    for i, rng in enumerate(args.ranges):
        parts = rng.split("-", 1)
        if len(parts) != 2:
            _err(f"Invalid range {rng!r}. Expected START-END e.g. 01:00-02:30")
            return 1
        try:
            tr = parse_range(parts[0].strip(), parts[1].strip())
        except ValueError as exc:
            _err(str(exc))
            return 1

        label = args.label if args.label and len(args.ranges) == 1 else None
        clips.append(
            ClipSpec(
                time_range=tr,
                highlight=args.highlight,
                compress=compress,
                aspect_ratio=aspect,
                label=label or f"clip_{i+1:02d}",
            )
        )

    out_dir = Path(args.output)
    mode = "re-encode" if compress else "stream-copy (lossless)"
    ar_str = f" · aspect {args.aspect}" if getattr(args, "aspect", None) else ""

    print(f"  {_bold('source')}   {input_path}")
    print(f"  {_bold('output')}   {out_dir}")
    print(f"  {_bold('clips')}    {len(clips)}")
    print(f"  {_bold('mode')}     {mode}{ar_str}")
    if args.highlight:
        print(f"  {_bold('highlight')} enabled → {out_dir / 'highlights'}")
    _rule()

    t0 = time.perf_counter()

    def on_progress(idx: int, total: int, result: ClipResult) -> None:
        _print_result(idx, total, result)

    results = clipflow.trim(
        input_path,
        clips,
        output_dir=out_dir,
        on_progress=on_progress,
    )

    _rule()
    ok_count = sum(1 for r in results if r.ok)
    fail_count = len(results) - ok_count
    total_s = time.perf_counter() - t0

    summary_parts = [_green(f"{ok_count} ok")]
    if fail_count:
        summary_parts.append(_red(f"{fail_count} failed"))
    print(f"  {' · '.join(summary_parts)}  {_dim(f'{total_s:.2f}s total')}")
    print()

    return 0 if fail_count == 0 else 1


# ---------------------------------------------------------------------------
# `clipflow inspect`
# ---------------------------------------------------------------------------

def _cmd_inspect(args: argparse.Namespace) -> int:
    """
    clipflow inspect input.mp4 [--json]
    """
    _banner()

    input_path = Path(args.input)
    if not input_path.exists():
        _err(f"File not found: {input_path}")
        return 1

    try:
        info = clipflow.inspect(input_path)
    except Exception as exc:
        _err(str(exc))
        return 1

    if args.json:
        out = {
            "path": str(info.path),
            "duration_s": info.duration_s,
            "duration_fmt": info.duration_fmt,
            "width": info.width,
            "height": info.height,
            "resolution": info.resolution,
            "fps": round(info.fps, 3),
            "video_codec": info.video_codec,
            "audio_codec": info.audio_codec,
            "size_bytes": info.size_bytes,
            "size_mb": info.size_mb,
        }
        print(json.dumps(out, indent=2))
        return 0

    print(f"  {_bold(input_path.name)}")
    _rule()
    _info("Duration ",   _bold(info.duration_fmt))
    _info("Resolution",  _bold(info.resolution))
    _info("FPS      ",   _bold(f"{info.fps:.3f}"))
    _info("Video    ",   _bold(info.video_codec))
    _info("Audio    ",   _bold(info.audio_codec or "none"))
    _info("Size     ",   _bold(f"{info.size_mb} MB"))
    _info("Path     ",   _dim(str(info.path)))
    print()
    return 0


# ---------------------------------------------------------------------------
# `clipflow batch`
# ---------------------------------------------------------------------------

_BATCH_SCHEMA_EXAMPLE = textwrap.dedent("""
  JSON spec file format
  ─────────────────────
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
          "compress": "medium",
          "aspect": "16:9"
        },
        {
          "start": "10:00",
          "end":   "11:30",
          "label": "key_moment",
          "highlight": true
        }
      ]
    }
  ]
""").strip()


def _parse_batch_json(path: Path) -> list[BatchSpec]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Batch JSON must be a top-level list of objects.")

    specs: list[BatchSpec] = []
    for entry in raw:
        input_path = Path(entry["input"])
        output_dir = Path(entry.get("output_dir", "output"))
        batch_spec = BatchSpec(input_path=input_path, output_dir=output_dir)

        for clip_def in entry.get("clips", []):
            tr = parse_range(clip_def["start"], clip_def["end"])
            compress_name: str | None = clip_def.get("compress")
            compress_obj: CompressOptions | None = None
            if compress_name:
                preset_map = {
                    "low":    clipflow.COMPRESS_LOW,
                    "medium": clipflow.COMPRESS_MEDIUM,
                    "high":   clipflow.COMPRESS_HIGH,
                }
                if compress_name not in preset_map:
                    raise ValueError(
                        f"compress must be low|medium|high, got {compress_name!r}"
                    )
                compress_obj = preset_map[compress_name]

            aspect_obj = _parse_aspect(clip_def.get("aspect"))
            batch_spec.add(
                ClipSpec(
                    time_range=tr,
                    highlight=clip_def.get("highlight", False),
                    compress=compress_obj,
                    aspect_ratio=aspect_obj,
                    label=clip_def.get("label"),
                )
            )

        specs.append(batch_spec)
    return specs


def _cmd_batch(args: argparse.Namespace) -> int:
    """
    clipflow batch spec.json
    """
    _banner()

    spec_path = Path(args.spec)
    if not spec_path.exists():
        _err(f"Spec file not found: {spec_path}")
        return 1

    try:
        specs = _parse_batch_json(spec_path)
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        _err(f"Invalid spec file: {exc}")
        print()
        print(_dim(_BATCH_SCHEMA_EXAMPLE))
        return 1

    total_clips = sum(len(s.clips) for s in specs)
    print(f"  {_bold('spec')}    {spec_path}")
    print(f"  {_bold('inputs')} {len(specs)}  ({total_clips} clips total)")
    _rule()

    processed = 0
    failed = 0
    t0 = time.perf_counter()

    def on_progress(idx: int, total: int, result: ClipResult) -> None:
        nonlocal processed, failed
        processed += 1
        if not result.ok:
            failed += 1
        _print_result(idx, total, result)

    clipflow.batch(specs, on_progress=on_progress)

    _rule()
    ok_count = processed - failed
    total_s = time.perf_counter() - t0
    summary_parts = [_green(f"{ok_count} ok")]
    if failed:
        summary_parts.append(_red(f"{failed} failed"))
    print(f"  {' · '.join(summary_parts)}  {_dim(f'{total_s:.2f}s total')}")
    print()
    return 0 if failed == 0 else 1


# ---------------------------------------------------------------------------
# Root parser
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="clipflow",
        description="Trim, compress, and highlight video clips via ffmpeg.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            examples:
              # stream-copy trim (lossless, fast)
              clipflow trim lecture.mp4 01:00-02:30

              # multiple ranges
              clipflow trim lecture.mp4 00:00-01:00 10:30-12:00 --output clips/

              # compress to H.264 high quality, crop to 16:9, mark as highlight
              clipflow trim concert.mp4 05:00-06:30 --compress high --aspect 16:9 --highlight

              # custom CRF
              clipflow trim raw.mp4 00:00-30:00 --crf 20 --codec libx265

              # inspect metadata
              clipflow inspect documentary.mp4
              clipflow inspect documentary.mp4 --json

              # batch from JSON spec
              clipflow batch spec.json
        """),
    )
    parser.add_argument(
        "--version", action="version", version=f"clipflow {clipflow.__version__}"
    )

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # ── trim ─────────────────────────────────────────────────────────────────
    p_trim = sub.add_parser(
        "trim",
        help="Trim one or more time ranges from a video",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent("""
            Trim segments from a video file.

            Each RANGE is  START-END  where START / END accept:
              MM:SS        01:30
              HH:MM:SS     01:02:03
              plain secs   90

            Without --compress the output is a lossless stream-copy
            (very fast, no quality loss).
        """),
    )
    p_trim.add_argument("input", metavar="INPUT", help="Source video file")
    p_trim.add_argument(
        "ranges",
        metavar="RANGE",
        nargs="+",
        help="Time range(s) to extract, e.g. 01:00-02:30",
    )
    p_trim.add_argument(
        "-o", "--output",
        default="output",
        metavar="DIR",
        help="Output directory  [default: output]",
    )
    p_trim.add_argument(
        "--label",
        metavar="NAME",
        help="Filename label for the clip (single-range only)",
    )
    p_trim.add_argument(
        "--highlight",
        action="store_true",
        help="Also copy clip(s) to OUTPUT/highlights/",
    )
    _add_compress_args(p_trim)
    _add_aspect_args(p_trim)
    p_trim.set_defaults(func=_cmd_trim)

    # ── inspect ──────────────────────────────────────────────────────────────
    p_inspect = sub.add_parser(
        "inspect",
        help="Print metadata about a video file",
        description="Print duration, resolution, codecs, fps, and file size.",
    )
    p_inspect.add_argument("input", metavar="INPUT", help="Video file to inspect")
    p_inspect.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON (for scripting)",
    )
    p_inspect.set_defaults(func=_cmd_inspect)

    # ── batch ─────────────────────────────────────────────────────────────────
    p_batch = sub.add_parser(
        "batch",
        help="Process multiple clips from a JSON spec file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=_BATCH_SCHEMA_EXAMPLE,
    )
    p_batch.add_argument("spec", metavar="SPEC", help="Path to batch JSON spec file")
    p_batch.set_defaults(func=_cmd_batch)

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
