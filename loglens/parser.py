"""Parsing helpers for supported log lines."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re

from .models import LEVELS, LogRecord


LINE_RE = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) "
    r"(?P<level>[A-Z]+) "
    r"(?P<module>[A-Za-z0-9_.-]+) - "
    r"(?P<message>.*)$"
)


@dataclass(frozen=True)
class ParseOutcome:
    """Detailed result for a single parsed line."""

    record: LogRecord | None
    error: str | None = None


def parse_log_line(line: str) -> LogRecord | None:
    """Parse one non-empty log line.

    Returns ``None`` when the line does not match the supported format.
    """

    return parse_log_line_detailed(line).record


def parse_log_line_detailed(line: str) -> ParseOutcome:
    """Parse one non-empty log line with a user-facing failure reason."""

    match = LINE_RE.match(line)
    if match is None:
        return ParseOutcome(None, "line does not match expected log format")

    timestamp = match.group("timestamp")
    try:
        datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return ParseOutcome(None, f"invalid timestamp '{timestamp}'")

    level = match.group("level")
    if level not in LEVELS:
        allowed = ", ".join(LEVELS)
        return ParseOutcome(None, f"unsupported log level '{level}'. Allowed levels: {allowed}")

    return ParseOutcome(
        LogRecord(
            timestamp=timestamp,
            level=level,
            module=match.group("module"),
            message=match.group("message"),
        )
    )
