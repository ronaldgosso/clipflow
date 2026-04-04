"""
Tests for clipflow — Phase 1
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Covers:
- parse_seconds / parse_range
- TimeRange / ClipSpec / CompressOptions validation
- _ffmpeg._build_trim_command  (no subprocess called)
- _ffmpeg.build_aspect_ratio_filter
- core.trim  (subprocess patched via monkeypatch)
- core.inspect (subprocess patched)
- ClipResult highlight path routing
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import clipflow
from clipflow._ffmpeg import _build_trim_command, build_aspect_ratio_filter
from clipflow._ffmpeg_manager import reset_cache
from clipflow.models import (
    COMPRESS_HIGH,
    COMPRESS_MEDIUM,
    ClipSpec,
    CompressOptions,
    TimeRange,
)
from clipflow.parser import parse_range, parse_seconds

# ===========================================================================
# Parser
# ===========================================================================


class TestParseSeconds:
    def test_plain_int(self):
        assert parse_seconds(90) == 90.0

    def test_plain_float(self):
        assert parse_seconds(1.5) == 1.5

    def test_string_int(self):
        assert parse_seconds("90") == 90.0

    def test_string_float(self):
        assert parse_seconds("90.5") == 90.5

    def test_mm_ss(self):
        assert parse_seconds("01:30") == 90.0

    def test_mm_ss_fractional(self):
        assert parse_seconds("01:30.5") == 90.5

    def test_hh_mm_ss(self):
        assert parse_seconds("01:02:03") == 3723.0

    def test_hh_mm_ss_zero_h(self):
        assert parse_seconds("00:01:30") == 90.0

    def test_invalid_string(self):
        with pytest.raises(ValueError, match="Cannot parse"):
            parse_seconds("not_a_time")

    def test_negative_rejected_by_timerange(self):
        # parse_seconds accepts negatives; TimeRange rejects them
        with pytest.raises(ValueError, match="start must be"):
            TimeRange(start=-1.0, end=10.0)


class TestParseRange:
    def test_strings(self):
        r = parse_range("01:00", "02:00")
        assert r.start == 60.0
        assert r.end == 120.0

    def test_ints(self):
        r = parse_range(60, 120)
        assert r.start == 60.0
        assert r.end == 120.0

    def test_mixed(self):
        r = parse_range("01:00", 120)
        assert r.end == 120.0

    def test_end_before_start_raises(self):
        with pytest.raises(ValueError, match="greater than start"):
            parse_range("02:00", "01:00")

    def test_equal_raises(self):
        with pytest.raises(ValueError, match="greater than start"):
            parse_range(60, 60)


# ===========================================================================
# Models
# ===========================================================================


class TestTimeRange:
    def test_duration(self):
        r = TimeRange(start=60.0, end=90.0)
        assert r.duration == 30.0

    def test_frozen(self):
        r = TimeRange(start=0.0, end=10.0)
        with pytest.raises(AttributeError):
            r.start = 5.0  # type: ignore[misc]

    def test_repr(self):
        r = TimeRange(start=0.0, end=90.0)
        assert "01:30" in repr(r)


class TestCompressOptions:
    def test_defaults(self):
        c = CompressOptions()
        assert c.crf == 23
        assert c.preset == "medium"
        assert c.codec == "libx264"

    def test_invalid_crf(self):
        with pytest.raises(ValueError, match="crf must be"):
            CompressOptions(crf=52)

    def test_invalid_preset(self):
        with pytest.raises(ValueError, match="preset must be"):
            CompressOptions(preset="turbo")

    def test_named_presets(self):
        assert COMPRESS_HIGH.crf == 18
        assert COMPRESS_MEDIUM.crf == 23


class TestClipSpec:
    def test_effective_label_default(self):
        spec = ClipSpec(TimeRange(start=60.0, end=120.0))
        assert "0060s" in spec.effective_label()
        assert "0120s" in spec.effective_label()

    def test_effective_label_custom(self):
        spec = ClipSpec(TimeRange(start=0.0, end=10.0), label="intro")
        assert spec.effective_label() == "intro"

    def test_highlight_default_false(self):
        spec = ClipSpec(TimeRange(start=0.0, end=5.0))
        assert spec.highlight is False


# ===========================================================================
# FFmpeg command builder (no subprocess)
# ===========================================================================


class TestBuildTrimCommand:
    def test_stream_copy_no_compress(self, tmp_path: Path):
        fake_ffmpeg = tmp_path / "ffmpeg.exe"
        fake_ffmpeg.write_bytes(b"")
        with patch(
            "clipflow._ffmpeg.ensure_ffmpeg",
            return_value=(fake_ffmpeg, fake_ffmpeg),
        ):
            cmd = _build_trim_command(
                Path("in.mp4"),
                Path("out.mp4"),
                start=60.0,
                duration=30.0,
            )
        assert "-c" in cmd
        copy_idx = cmd.index("-c")
        assert cmd[copy_idx + 1] == "copy"
        # seek before input in stream-copy mode
        ss_idx = cmd.index("-ss")
        i_idx = cmd.index("-i")
        assert ss_idx < i_idx

    def test_compress_mode_seek_after_input(self, tmp_path: Path):
        fake_ffmpeg = tmp_path / "ffmpeg.exe"
        fake_ffmpeg.write_bytes(b"")
        with patch(
            "clipflow._ffmpeg.ensure_ffmpeg",
            return_value=(fake_ffmpeg, fake_ffmpeg),
        ):
            cmd = _build_trim_command(
                Path("in.mp4"),
                Path("out.mp4"),
                start=60.0,
                duration=30.0,
                crf=23,
                preset="medium",
                codec="libx264",
            )
        # seek must come after -i in re-encode mode
        i_idx = cmd.index("-i")
        ss_idx = cmd.index("-ss", i_idx)  # find -ss AFTER -i
        assert ss_idx > i_idx

    def test_compress_flags_present(self, tmp_path: Path):
        fake_ffmpeg = tmp_path / "ffmpeg.exe"
        fake_ffmpeg.write_bytes(b"")
        with patch(
            "clipflow._ffmpeg.ensure_ffmpeg",
            return_value=(fake_ffmpeg, fake_ffmpeg),
        ):
            cmd = _build_trim_command(
                Path("in.mp4"),
                Path("out.mp4"),
                start=0.0,
                duration=60.0,
                crf=18,
                preset="slow",
                codec="libx265",
            )
        assert "-crf" in cmd
        assert cmd[cmd.index("-crf") + 1] == "18"
        assert cmd[cmd.index("-preset") + 1] == "slow"
        assert cmd[cmd.index("-c:v") + 1] == "libx265"

    def test_audio_bitrate(self, tmp_path: Path):
        fake_ffmpeg = tmp_path / "ffmpeg.exe"
        fake_ffmpeg.write_bytes(b"")
        with patch(
            "clipflow._ffmpeg.ensure_ffmpeg",
            return_value=(fake_ffmpeg, fake_ffmpeg),
        ):
            cmd = _build_trim_command(
                Path("in.mp4"),
                Path("out.mp4"),
                start=0.0,
                duration=30.0,
                crf=23,
                preset="medium",
                codec="libx264",
                audio_bitrate="192k",
            )
        assert "-b:a" in cmd
        assert cmd[cmd.index("-b:a") + 1] == "192k"

    def test_overwrite_flag(self, tmp_path: Path):
        fake_ffmpeg = tmp_path / "ffmpeg.exe"
        fake_ffmpeg.write_bytes(b"")
        with patch(
            "clipflow._ffmpeg.ensure_ffmpeg",
            return_value=(fake_ffmpeg, fake_ffmpeg),
        ):
            cmd = _build_trim_command(
                Path("in.mp4"), Path("out.mp4"), start=0.0, duration=10.0
            )
        assert "-y" in cmd


class TestAspectRatioFilter:
    def test_returns_string(self):
        f = build_aspect_ratio_filter(16, 9)
        assert isinstance(f, str)
        assert "crop=" in f

    def test_different_ratios_differ(self):
        f169 = build_aspect_ratio_filter(16, 9)
        f916 = build_aspect_ratio_filter(9, 16)
        assert f169 != f916


# ===========================================================================
# core.trim (subprocess mocked)
# ===========================================================================

FAKE_PROBE = {
    "format": {
        "duration": "120.0",
        "size": "10485760",
    },
    "streams": [
        {
            "codec_type": "video",
            "codec_name": "h264",
            "width": 1920,
            "height": 1080,
            "r_frame_rate": "30/1",
        },
        {
            "codec_type": "audio",
            "codec_name": "aac",
        },
    ],
}


def _make_fake_run(returncode: int = 0):
    """Return a subprocess.run replacement that does nothing harmful."""

    def fake_run(cmd, *, check, capture_output=False, text=False):
        mock = MagicMock()
        mock.returncode = returncode
        mock.stdout = json.dumps(FAKE_PROBE)
        mock.stderr = b""
        if check and returncode != 0:
            raise subprocess.CalledProcessError(returncode, cmd)
        return mock

    return fake_run


@pytest.fixture()
def tmp_video(tmp_path: Path) -> Path:
    """Create a zero-byte fake video file so Path.exists() passes."""
    v = tmp_path / "sample.mp4"
    v.write_bytes(b"")
    return v


@pytest.fixture(autouse=True)
def mock_ffmpeg_manager(tmp_path: Path):
    """
    Mock ensure_ffmpeg to return fake binary paths.
    This fixture auto-use applies to all tests in this file.
    """
    fake_ffmpeg = tmp_path / "fake_ffmpeg.exe"
    fake_ffprobe = tmp_path / "fake_ffprobe.exe"
    fake_ffmpeg.write_bytes(b"")
    fake_ffprobe.write_bytes(b"")

    with patch(
        "clipflow._ffmpeg_manager.ensure_ffmpeg",
        return_value=(fake_ffmpeg, fake_ffprobe),
    ):
        yield


@pytest.fixture()
def mock_ffmpeg_manager_reset():
    """Allow tests to call reset_cache() without affecting other tests."""
    yield
    reset_cache()


class TestTrimAPI:
    def test_single_clip_ok(self, tmp_video: Path, tmp_path: Path):
        spec = ClipSpec(parse_range("00:00", "01:00"), label="intro")
        with patch("clipflow._ffmpeg.subprocess.run", side_effect=_make_fake_run()):
            results = clipflow.trim(tmp_video, spec, output_dir=tmp_path / "out")

        assert len(results) == 1
        assert results[0].ok
        assert results[0].spec.label == "intro"

    def test_file_not_found(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            clipflow.trim("nonexistent.mp4", ClipSpec(parse_range("0", "10")))

    def test_highlight_path_set(self, tmp_video: Path, tmp_path: Path):
        spec = ClipSpec(
            parse_range("00:00", "01:00"),
            highlight=True,
            label="moment",
        )
        out_dir = tmp_path / "out"

        def fake_run(cmd, *, check, capture_output=False, text=False):
            # Create the output file so copy_file can proceed
            out = Path(cmd[-1])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"fakevideo")
            m = MagicMock()
            m.returncode = 0
            m.stderr = b""
            return m

        with patch("clipflow._ffmpeg.subprocess.run", side_effect=fake_run):
            results = clipflow.trim(tmp_video, spec, output_dir=out_dir)

        assert results[0].ok
        assert results[0].highlight_path is not None
        assert "highlights" in str(results[0].highlight_path)

    def test_multiple_clips(self, tmp_video: Path, tmp_path: Path):
        clips = [
            ClipSpec(parse_range("00:00", "01:00"), label=f"clip_{i}") for i in range(3)
        ]
        with patch("clipflow._ffmpeg.subprocess.run", side_effect=_make_fake_run()):
            results = clipflow.trim(tmp_video, clips, output_dir=tmp_path / "out")

        assert len(results) == 3

    def test_on_progress_called(self, tmp_video: Path, tmp_path: Path):
        progress_calls = []

        def on_prog(idx, total, result):
            progress_calls.append((idx, total))

        clips = [ClipSpec(parse_range(str(i * 10), str(i * 10 + 10))) for i in range(2)]
        with patch("clipflow._ffmpeg.subprocess.run", side_effect=_make_fake_run()):
            clipflow.trim(
                tmp_video, clips, output_dir=tmp_path / "out", on_progress=on_prog
            )

        assert progress_calls == [(1, 2), (2, 2)]

    def test_ffmpeg_error_returns_failed_result(self, tmp_video: Path, tmp_path: Path):
        def bad_run(cmd, *, check, capture_output=False, text=False):
            raise subprocess.CalledProcessError(1, cmd, stderr=b"encoder error")

        spec = ClipSpec(parse_range("0", "10"), label="bad")
        with patch("clipflow._ffmpeg.subprocess.run", side_effect=bad_run):
            results = clipflow.trim(tmp_video, spec, output_dir=tmp_path / "out")

        assert not results[0].ok
        assert results[0].error is not None


# ===========================================================================
# core.inspect (subprocess mocked)
# ===========================================================================


class TestInspectAPI:
    def test_returns_video_info(self, tmp_video: Path):
        with patch("clipflow._ffmpeg.subprocess.run", side_effect=_make_fake_run()):
            info = clipflow.inspect(tmp_video)

        assert info.width == 1920
        assert info.height == 1080
        assert info.fps == 30.0
        assert info.video_codec == "h264"
        assert info.audio_codec == "aac"
        assert info.duration_s == 120.0
        assert info.resolution == "1920×1080"
        assert "02:00" in info.duration_fmt

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            clipflow.inspect("ghost.mp4")


# ===========================================================================
# Public API surface check
# ===========================================================================


class TestPublicAPI:
    def test_all_exports_present(self):
        for name in clipflow.__all__:
            assert hasattr(clipflow, name), f"Missing export: {name}"

    def test_version(self):
        assert isinstance(clipflow.__version__, str)
        assert clipflow.__version__.count(".") == 2
