"""File analysis logic for LogLens."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable

from .models import LEVELS, AnalysisResult, LogRecord
from .parser import parse_log_line_detailed


class LogLensError(Exception):
    """Base error for user-facing LogLens failures."""


class LogFileError(LogLensError):
    """Raised when a log file cannot be read."""


class StrictModeError(LogLensError):
    """Raised when strict mode encounters an invalid non-empty log line."""

    def __init__(self, line_number: int, reason: str) -> None:
        self.line_number = line_number
        self.reason = reason
        super().__init__(f"Invalid log line at {line_number}: {reason}")


def analyze_file(
    path: Path,
    *,
    levels: Iterable[str] | None = None,
    contains: str | None = None,
    modules: Iterable[str] | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    strict: bool = False,
) -> AnalysisResult:
    """Analyze a log file and return counts plus filtered records."""

    selected_levels = set(levels or [])
    selected_modules = set(modules or [])
    keyword = contains.casefold() if contains else None

    valid_lines = 0
    invalid_lines = 0
    level_counts = {level: 0 for level in LEVELS}
    records: list[LogRecord] = []

    try:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                line = raw_line.rstrip("\n\r")
                if not line.strip():
                    continue

                outcome = parse_log_line_detailed(line)
                record = outcome.record
                if record is None:
                    if strict:
                        reason = outcome.error or "invalid log line"
                        raise StrictModeError(line_number, reason)
                    invalid_lines += 1
                    continue

                valid_lines += 1
                level_counts[record.level] += 1

                if selected_levels and record.level not in selected_levels:
                    continue
                if selected_modules and record.module not in selected_modules:
                    continue
                record_time = datetime.strptime(record.timestamp, "%Y-%m-%d %H:%M:%S")
                if since is not None and record_time < since:
                    continue
                if until is not None and record_time > until:
                    continue
                if keyword and keyword not in record.message.casefold():
                    continue
                records.append(record)
    except StrictModeError:
        raise
    except FileNotFoundError as exc:
        raise LogFileError(f"Log file not found: {path}") from exc
    except IsADirectoryError as exc:
        raise LogFileError(f"Expected a log file but found a directory: {path}") from exc
    except PermissionError as exc:
        raise LogFileError(f"Permission denied while reading log file: {path}") from exc
    except UnicodeDecodeError as exc:
        raise LogFileError(f"Could not read log file as UTF-8 text: {path}") from exc
    except OSError as exc:
        raise LogFileError(f"Could not read log file '{path}': {exc.strerror or exc}") from exc

    return AnalysisResult(
        valid_lines=valid_lines,
        invalid_lines=invalid_lines,
        level_counts=level_counts,
        records=records,
    )
