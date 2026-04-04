"""
Tests for clipflow CLI — Phase 2
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Strategy: invoke main() / subcommand functions directly with parsed
Namespace objects, patching clipflow.trim / inspect / batch at the
module boundary.  No subprocess ever runs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import patch

import pytest

import clipflow
from clipflow.cli import (
    _build_parser,
    _cmd_batch,
    _cmd_inspect,
    _cmd_trim,
    _parse_aspect,
    _parse_batch_json,
    main,
)
from clipflow.models import (
    AR_9_16,
    AR_16_9,
    ClipResult,
    ClipSpec,
    TimeRange,
    VideoInfo,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_video(tmp_path: Path) -> Path:
    v = tmp_path / "sample.mp4"
    v.write_bytes(b"")
    return v


def _make_result(label: str = "clip", ok: bool = True) -> ClipResult:
    return ClipResult(
        spec=ClipSpec(TimeRange(0.0, 10.0), label=label),
        output_path=Path(f"output/{label}.mp4"),
        highlight_path=None,
        duration_s=0.42,
        ok=ok,
        error=None if ok else "ffmpeg error",
    )


def _make_info(path: Path) -> VideoInfo:
    return VideoInfo(
        path=path,
        duration_s=120.0,
        width=1920,
        height=1080,
        fps=30.0,
        video_codec="h264",
        audio_codec="aac",
        size_bytes=10_485_760,
    )


# ---------------------------------------------------------------------------
# _parse_aspect
# ---------------------------------------------------------------------------


class TestParseAspect:
    def test_none_returns_none(self):
        assert _parse_aspect(None) is None

    def test_named_16_9(self):
        ar = _parse_aspect("16:9")
        assert ar == AR_16_9

    def test_named_9_16(self):
        ar = _parse_aspect("9:16")
        assert ar == AR_9_16

    def test_custom(self):
        ar = _parse_aspect("21:9")
        assert ar is not None
        assert ar.width == 21
        assert ar.height == 9

    def test_invalid_raises(self):
        with pytest.raises(argparse.ArgumentTypeError):
            _parse_aspect("widescreen")


# ---------------------------------------------------------------------------
# Parser structure
# ---------------------------------------------------------------------------


class TestParserStructure:
    def test_version_flag(self, capsys: pytest.CaptureFixture[str]):
        parser = _build_parser()
        with pytest.raises(SystemExit) as exc:
            parser.parse_args(["--version"])
        assert exc.value.code == 0
        captured = capsys.readouterr()
        assert clipflow.__version__ in (captured.out + captured.err)

    def test_no_command_exits(self):
        with pytest.raises(SystemExit):
            _build_parser().parse_args([])

    def test_trim_subcommand_parses(self):
        parser = _build_parser()
        ns = parser.parse_args(["trim", "input.mp4", "01:00-02:00"])
        assert ns.command == "trim"
        assert ns.input == "input.mp4"
        assert ns.ranges == ["01:00-02:00"]

    def test_trim_multiple_ranges(self):
        parser = _build_parser()
        ns = parser.parse_args(["trim", "v.mp4", "00:00-01:00", "05:00-06:00"])
        assert len(ns.ranges) == 2

    def test_trim_compress_flag(self):
        parser = _build_parser()
        ns = parser.parse_args(["trim", "v.mp4", "00:00-01:00", "--compress", "high"])
        assert ns.compress == "high"

    def test_trim_highlight_flag(self):
        parser = _build_parser()
        ns = parser.parse_args(["trim", "v.mp4", "00:00-01:00", "--highlight"])
        assert ns.highlight is True

    def test_trim_output_flag(self):
        parser = _build_parser()
        ns = parser.parse_args(["trim", "v.mp4", "00:00-01:00", "-o", "my_clips"])
        assert ns.output == "my_clips"

    def test_inspect_subcommand_parses(self):
        parser = _build_parser()
        ns = parser.parse_args(["inspect", "video.mp4"])
        assert ns.command == "inspect"

    def test_inspect_json_flag(self):
        parser = _build_parser()
        ns = parser.parse_args(["inspect", "video.mp4", "--json"])
        assert ns.json is True

    def test_batch_subcommand_parses(self):
        parser = _build_parser()
        ns = parser.parse_args(["batch", "spec.json"])
        assert ns.command == "batch"
        assert ns.spec == "spec.json"


# ---------------------------------------------------------------------------
# _cmd_trim
# ---------------------------------------------------------------------------


class TestCmdTrim:
    def _args(self, tmp_video: Path, ranges: list[str], **kwargs) -> argparse.Namespace:
        defaults = {
            "input": str(tmp_video),
            "ranges": ranges,
            "output": "output",
            "label": None,
            "highlight": False,
            "compress": None,
            "crf": None,
            "codec": "libx264",
            "audio_bitrate": None,
            "aspect": None,
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def test_single_range_ok(self, tmp_video: Path):
        args = self._args(tmp_video, ["01:00-02:00"])
        with patch("clipflow.cli.clipflow.trim", return_value=[_make_result()]) as m:
            rc = _cmd_trim(args)
        assert rc == 0
        m.assert_called_once()

    def test_returns_1_on_failure(self, tmp_video: Path):
        args = self._args(tmp_video, ["00:00-01:00"])
        with patch("clipflow.cli.clipflow.trim", return_value=[_make_result(ok=False)]):
            rc = _cmd_trim(args)
        assert rc == 1

    def test_missing_file_returns_1(self, tmp_path: Path):
        args = argparse.Namespace(
            input=str(tmp_path / "ghost.mp4"),
            ranges=["00:00-01:00"],
            output="out",
            label=None,
            highlight=False,
            compress=None,
            crf=None,
            codec="libx264",
            audio_bitrate=None,
            aspect=None,
        )
        rc = _cmd_trim(args)
        assert rc == 1

    def test_invalid_range_format_returns_1(self, tmp_video: Path):
        args = self._args(tmp_video, ["not-a-range-at-all"])
        rc = _cmd_trim(args)
        assert rc == 1

    def test_compress_high_passed_through(self, tmp_video: Path):
        args = self._args(tmp_video, ["00:00-01:00"], compress="high")
        captured_clips: list[ClipSpec] = []

        def fake_trim(path, clips, **kw):
            captured_clips.extend(clips if isinstance(clips, list) else [clips])
            return [_make_result()]

        with patch("clipflow.cli.clipflow.trim", side_effect=fake_trim):
            _cmd_trim(args)

        assert captured_clips[0].compress is not None
        assert captured_clips[0].compress.crf == 18  # COMPRESS_HIGH

    def test_highlight_flag_sets_spec(self, tmp_video: Path):
        args = self._args(tmp_video, ["00:00-01:00"], highlight=True)
        captured_clips: list[ClipSpec] = []

        def fake_trim(path, clips, **kw):
            captured_clips.extend(clips if isinstance(clips, list) else [clips])
            return [_make_result()]

        with patch("clipflow.cli.clipflow.trim", side_effect=fake_trim):
            _cmd_trim(args)

        assert captured_clips[0].highlight is True

    def test_aspect_ratio_parsed(self, tmp_video: Path):
        args = self._args(tmp_video, ["00:00-01:00"], aspect="16:9")
        captured_clips: list[ClipSpec] = []

        def fake_trim(path, clips, **kw):
            captured_clips.extend(clips if isinstance(clips, list) else [clips])
            return [_make_result()]

        with patch("clipflow.cli.clipflow.trim", side_effect=fake_trim):
            _cmd_trim(args)

        assert captured_clips[0].aspect_ratio == AR_16_9

    def test_multiple_ranges_produce_multiple_clips(self, tmp_video: Path):
        args = self._args(tmp_video, ["00:00-01:00", "02:00-03:00", "04:00-05:00"])
        captured_clips: list[ClipSpec] = []

        def fake_trim(path, clips, **kw):
            captured_clips.extend(clips)
            return [_make_result(f"c{i}") for i in range(len(clips))]

        with patch("clipflow.cli.clipflow.trim", side_effect=fake_trim):
            _cmd_trim(args)

        assert len(captured_clips) == 3

    def test_on_progress_callback_fires(
        self, tmp_video: Path, capsys: pytest.CaptureFixture[str]
    ):
        args = self._args(tmp_video, ["00:00-01:00"])

        def fake_trim(path, clips, *, output_dir, on_progress=None):
            r = _make_result("intro")
            if on_progress:
                on_progress(1, 1, r)
            return [r]

        with patch("clipflow.cli.clipflow.trim", side_effect=fake_trim):
            _cmd_trim(args)

        out = capsys.readouterr().out
        assert "intro" in out

    def test_highlight_path_shown_in_output(
        self, tmp_video: Path, capsys: pytest.CaptureFixture[str]
    ):
        args = self._args(tmp_video, ["00:00-01:00"], highlight=True)
        result_with_hl = ClipResult(
            spec=ClipSpec(TimeRange(0.0, 10.0), label="moment"),
            output_path=Path("output/moment.mp4"),
            highlight_path=Path("output/highlights/moment.mp4"),
            duration_s=0.1,
            ok=True,
        )

        def fake_trim(path, clips, *, output_dir, on_progress=None):
            if on_progress:
                on_progress(1, 1, result_with_hl)
            return [result_with_hl]

        with patch("clipflow.cli.clipflow.trim", side_effect=fake_trim):
            _cmd_trim(args)

        out = capsys.readouterr().out
        assert "highlight" in out


# ---------------------------------------------------------------------------
# _cmd_inspect
# ---------------------------------------------------------------------------


class TestCmdInspect:
    def _args(self, path: Path, as_json: bool = False) -> argparse.Namespace:
        return argparse.Namespace(input=str(path), json=as_json)

    def test_human_output_ok(self, tmp_video: Path, capsys: pytest.CaptureFixture[str]):
        with patch("clipflow.cli.clipflow.inspect", return_value=_make_info(tmp_video)):
            rc = _cmd_inspect(self._args(tmp_video))
        assert rc == 0
        out = capsys.readouterr().out
        assert "1920" in out
        assert "h264" in out

    def test_json_output(self, tmp_video: Path, capsys: pytest.CaptureFixture[str]):
        with patch("clipflow.cli.clipflow.inspect", return_value=_make_info(tmp_video)):
            rc = _cmd_inspect(self._args(tmp_video, as_json=True))
        assert rc == 0
        raw = capsys.readouterr().out
        # Strip any non-JSON banner lines, find the JSON block
        json_start = raw.find("{")
        data = json.loads(raw[json_start:])
        assert data["width"] == 1920
        assert data["video_codec"] == "h264"
        assert "duration_fmt" in data

    def test_missing_file_returns_1(self, tmp_path: Path):
        args = self._args(tmp_path / "ghost.mp4")
        rc = _cmd_inspect(args)
        assert rc == 1

    def test_inspect_error_returns_1(self, tmp_video: Path):
        with patch(
            "clipflow.cli.clipflow.inspect", side_effect=RuntimeError("ffprobe missing")
        ):
            rc = _cmd_inspect(self._args(tmp_video))
        assert rc == 1


# ---------------------------------------------------------------------------
# _parse_batch_json + _cmd_batch
# ---------------------------------------------------------------------------


class TestBatchJson:
    def _write_spec(self, tmp_path: Path, data: object) -> Path:
        p = tmp_path / "spec.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        return p

    def test_valid_spec_parses(self, tmp_path: Path):
        spec_path = self._write_spec(
            tmp_path,
            [
                {
                    "input": "video.mp4",
                    "output_dir": "out",
                    "clips": [
                        {"start": "00:00", "end": "01:00", "label": "intro"},
                        {"start": "02:00", "end": "03:00", "highlight": True},
                    ],
                }
            ],
        )
        specs = _parse_batch_json(spec_path)
        assert len(specs) == 1
        assert len(specs[0].clips) == 2
        assert specs[0].clips[0].label == "intro"
        assert specs[0].clips[1].highlight is True

    def test_compress_parsed(self, tmp_path: Path):
        spec_path = self._write_spec(
            tmp_path,
            [
                {
                    "input": "v.mp4",
                    "clips": [{"start": "0", "end": "10", "compress": "high"}],
                }
            ],
        )
        specs = _parse_batch_json(spec_path)
        assert specs[0].clips[0].compress is not None
        assert specs[0].clips[0].compress.crf == 18

    def test_invalid_compress_raises(self, tmp_path: Path):
        spec_path = self._write_spec(
            tmp_path,
            [
                {
                    "input": "v.mp4",
                    "clips": [{"start": "0", "end": "10", "compress": "ultra"}],
                }
            ],
        )
        with pytest.raises(ValueError, match="low|medium|high"):
            _parse_batch_json(spec_path)

    def test_not_a_list_raises(self, tmp_path: Path):
        spec_path = self._write_spec(tmp_path, {"input": "v.mp4"})
        with pytest.raises(ValueError, match="top-level list"):
            _parse_batch_json(spec_path)

    def test_aspect_ratio_in_spec(self, tmp_path: Path):
        spec_path = self._write_spec(
            tmp_path,
            [
                {
                    "input": "v.mp4",
                    "clips": [{"start": "0", "end": "5", "aspect": "9:16"}],
                }
            ],
        )
        specs = _parse_batch_json(spec_path)
        assert specs[0].clips[0].aspect_ratio == AR_9_16


class TestCmdBatch:
    def _write_spec(self, tmp_path: Path, data: object) -> Path:
        p = tmp_path / "spec.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        return p

    def test_ok_batch_returns_0(self, tmp_path: Path):
        spec_path = self._write_spec(
            tmp_path, [{"input": "v.mp4", "clips": [{"start": "0", "end": "10"}]}]
        )
        args = argparse.Namespace(spec=str(spec_path))

        with patch("clipflow.cli.clipflow.batch", return_value={}):
            rc = _cmd_batch(args)
        assert rc == 0

    def test_missing_spec_returns_1(self, tmp_path: Path):
        args = argparse.Namespace(spec=str(tmp_path / "ghost.json"))
        rc = _cmd_batch(args)
        assert rc == 1

    def test_bad_json_returns_1(self, tmp_path: Path):
        bad = tmp_path / "bad.json"
        bad.write_text("not json!!!", encoding="utf-8")
        args = argparse.Namespace(spec=str(bad))
        rc = _cmd_batch(args)
        assert rc == 1


# ---------------------------------------------------------------------------
# main() entry point
# ---------------------------------------------------------------------------


class TestMainEntryPoint:
    def test_main_trim_dispatches(self, tmp_video: Path):
        with (
            patch("sys.argv", ["clipflow", "trim", str(tmp_video), "00:00-01:00"]),
            patch("clipflow.cli.clipflow.trim", return_value=[_make_result()]),
            pytest.raises(SystemExit) as exc,
        ):
            main()
        assert exc.value.code == 0

    def test_main_inspect_dispatches(self, tmp_video: Path):
        with (
            patch("sys.argv", ["clipflow", "inspect", str(tmp_video)]),
            patch("clipflow.cli.clipflow.inspect", return_value=_make_info(tmp_video)),
            pytest.raises(SystemExit) as exc,
        ):
            main()
        assert exc.value.code == 0

    def test_main_no_args_exits_nonzero(self):
        with (
            patch("sys.argv", ["clipflow"]),
            pytest.raises(SystemExit) as exc,
        ):
            main()
        assert exc.value.code != 0
