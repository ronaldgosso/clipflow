"""
examples/highlight_reel.py
~~~~~~~~~~~~~~~~~~~~~~~~~~
Real-world example: extract highlight clips from a long video,
compress them for social media, and export a JSON manifest.

Usage
-----
    python examples/highlight_reel.py input.mp4 --output reels/

The script will:
1. Inspect the source video and print metadata.
2. Extract 3 highlight clips at different time ranges.
3. Compress each to H.264 medium quality.
4. Crop the "vertical" clip to 9:16 for Reels/Shorts.
5. Write a manifest.json summarising all outputs.

No actual ffmpeg calls are made if the input file does not exist —
the script validates first and exits cleanly.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import clipflow
from clipflow import (
    AR_9_16,
    COMPRESS_MEDIUM,
    ClipResult,
    ClipSpec,
    parse_range,
)


def build_clips(duration_s: float) -> list[ClipSpec]:
    """
    Define the clips to extract.

    In a real workflow you'd read these from a spreadsheet,
    a subtitle file, or a scene-detection tool output.
    Here we hard-code three representative segments.
    """
    if duration_s < 300:
        print(f"  warning: video is only {duration_s:.0f}s — adjusting ranges")
        end = duration_s
        clips = [ClipSpec(parse_range(0, end), label="full", compress=COMPRESS_MEDIUM)]
        return clips

    return [
        ClipSpec(
            parse_range("00:00", "01:00"),
            label="opening",
            compress=COMPRESS_MEDIUM,
            highlight=True,
        ),
        ClipSpec(
            parse_range("02:30", "04:00"),
            label="key_moment",
            compress=COMPRESS_MEDIUM,
            highlight=True,
        ),
        ClipSpec(
            parse_range("04:30", "05:00"),
            label="vertical_short",
            compress=COMPRESS_MEDIUM,
            aspect_ratio=AR_9_16,  # crop to 9:16 for Reels / Shorts
            highlight=True,
        ),
    ]


def write_manifest(
    results: list[ClipResult],
    output_dir: Path,
    source_info: clipflow.VideoInfo,
) -> Path:
    """Write a JSON manifest of all produced clips."""
    entries = []
    for r in results:
        entry: dict = {
            "label": r.spec.effective_label(),
            "ok": r.ok,
            "duration_s": round(r.spec.time_range.duration, 3),
            "encode_time_s": round(r.duration_s, 3),
        }
        if r.ok:
            entry["output"] = str(r.output_path)
            if r.highlight_path:
                entry["highlight"] = str(r.highlight_path)
        else:
            entry["error"] = r.error
        entries.append(entry)

    manifest = {
        "source": str(source_info.path),
        "source_duration": source_info.duration_fmt,
        "source_resolution": source_info.resolution,
        "clips": entries,
        "total_ok": sum(1 for r in results if r.ok),
        "total_failed": sum(1 for r in results if not r.ok),
    }

    out = output_dir / "manifest.json"
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract highlight reel from a video.")
    parser.add_argument("input", help="Source video file")
    parser.add_argument("-o", "--output", default="reels", help="Output directory")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output)

    if not input_path.exists():
        print(f"error: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # ── 1. Inspect ────────────────────────────────────────────────────────
    print(f"\n  inspecting {input_path.name} …")
    info = clipflow.inspect(input_path)
    print(
        f"  {info.resolution}  {info.duration_fmt}  {info.fps:.2f}fps  {info.size_mb}MB"
    )

    # ── 2. Build clip list ────────────────────────────────────────────────
    clips = build_clips(info.duration_s)
    print(f"\n  {len(clips)} clips queued → {output_dir}/\n")

    # ── 3. Trim ───────────────────────────────────────────────────────────
    def on_progress(idx: int, total: int, result: ClipResult) -> None:
        label = result.spec.effective_label()
        if result.ok:
            print(f"  [{idx}/{total}] ✓ {label}  ({result.duration_s:.2f}s)")
            if result.highlight_path:
                print(f"          ★ highlight → {result.highlight_path.name}")
        else:
            print(f"  [{idx}/{total}] ✗ {label}  {result.error}", file=sys.stderr)

    results = clipflow.trim(
        input_path,
        clips,
        output_dir=output_dir,
        on_progress=on_progress,
    )

    # ── 4. Manifest ───────────────────────────────────────────────────────
    manifest_path = write_manifest(results, output_dir, info)
    ok = sum(1 for r in results if r.ok)
    print(f"\n  {ok}/{len(results)} clips produced")
    print(f"  manifest → {manifest_path}\n")

    sys.exit(0 if ok == len(results) else 1)


if __name__ == "__main__":
    main()
