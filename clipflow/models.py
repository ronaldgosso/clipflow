"""Data models for clipflow."""

from dataclasses import dataclass
from typing import Optional, List, Tuple

@dataclass(frozen=True)
class TimeRange:
    pass

@dataclass(frozen=True)
class ClipSpec:
    pass

@dataclass(frozen=True)
class CompressOptions:
    pass

@dataclass(frozen=True)
class AspectRatio:
    pass

@dataclass(frozen=True)
class ClipResult:
    pass

@dataclass(frozen=True)
class VideoInfo:
    pass

@dataclass(frozen=True)
class BatchSpec:
    pass
