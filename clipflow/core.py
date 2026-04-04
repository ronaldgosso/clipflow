"""Core API for clipflow."""

from .models import ClipResult, VideoInfo

def trim() -> ClipResult:
    """Trim a video."""
    pass

def inspect() -> VideoInfo:
    """Inspect a video."""
    pass

def batch() -> list[ClipResult]:
    """Batch process videos."""
    pass
