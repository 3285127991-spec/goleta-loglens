"""Shared data models for LogLens."""

from __future__ import annotations

from dataclasses import dataclass


LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


@dataclass(frozen=True)
class LogRecord:
    """A parsed log record."""

    timestamp: str
    level: str
    module: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {
            "timestamp": self.timestamp,
            "level": self.level,
            "module": self.module,
            "message": self.message,
        }


@dataclass(frozen=True)
class AnalysisResult:
    """Result returned by the analyzer."""

    valid_lines: int
    invalid_lines: int
    level_counts: dict[str, int]
    records: list[LogRecord]

    def as_dict(self) -> dict[str, object]:
        return {
            "valid_lines": self.valid_lines,
            "invalid_lines": self.invalid_lines,
            "level_counts": self.level_counts,
            "records": [record.as_dict() for record in self.records],
        }
