"""
clipflow.parser
~~~~~~~~~~~~~~~
Convert human-friendly time strings into seconds (float).

Supported formats
-----------------
``"MM:SS"``         → ``"01:30"``   = 90.0 s
``"HH:MM:SS"``      → ``"01:02:03"`` = 3723.0 s
``"SS"`` (int str)  → ``"90"``      = 90.0 s
``"SS.mmm"``        → ``"90.5"``    = 90.5 s
``float / int``     → direct pass-through
"""

from __future__ import annotations

import re

from clipflow.models import TimeRange

# Matches  HH:MM:SS, MM:SS, or plain seconds (with optional decimal)
_COLON_RE = re.compile(
    r"^(?:(?P<h>\d+):)?(?P<m>\d{1,2}):(?P<s>\d{1,2}(?:\.\d+)?)$"
)
_PLAIN_RE = re.compile(r"^\d+(\.\d+)?$")


def parse_seconds(value: str | int | float) -> float:
    """
    Convert *value* to seconds.

    Parameters
    ----------
    value:
        A time string (``"MM:SS"``, ``"HH:MM:SS"``, ``"90"``, ``"1.5"``),
        an integer, or a float.

    Returns
    -------
    float
        The equivalent number of seconds.

    Raises
    ------
    ValueError
        If *value* is a string that does not match any recognised format.
    """
    if isinstance(value, (int, float)):
        return float(value)

    s = str(value).strip()

    m = _COLON_RE.match(s)
    if m:
        h = int(m.group("h") or 0)
        mins = int(m.group("m"))
        secs = float(m.group("s"))
        return h * 3600 + mins * 60 + secs

    if _PLAIN_RE.match(s):
        return float(s)

    raise ValueError(
        f"Cannot parse time {value!r}. "
        "Expected 'HH:MM:SS', 'MM:SS', or a plain number of seconds."
    )


def parse_range(
    start: str | int | float,
    end: str | int | float,
) -> TimeRange:
    """
    Build a :class:`~clipflow.models.TimeRange` from two time values.

    Parameters
    ----------
    start:
        Start of the range (inclusive).
    end:
        End of the range (exclusive).

    Examples
    --------
    >>> parse_range("01:00", "01:30")
    TimeRange(01:00.000 → 01:30.000)

    >>> parse_range(60, 90)
    TimeRange(01:00.000 → 01:30.000)
    """
    return TimeRange(
        start=parse_seconds(start),
        end=parse_seconds(end),
    )
