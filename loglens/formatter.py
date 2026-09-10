"""Output formatters for analysis results."""

from __future__ import annotations

import json

from .models import LEVELS, AnalysisResult, LogRecord


def format_result(result: AnalysisResult, output_format: str) -> str:
    if output_format == "json":
        return json.dumps(result.as_dict(), indent=2) + "\n"
    if output_format == "text":
        return format_text(result)
    raise ValueError(f"Unsupported output format: {output_format}")


def format_text(result: AnalysisResult) -> str:
    lines = [
        f"Valid log lines: {result.valid_lines}",
        f"Invalid log lines: {result.invalid_lines}",
        "Level counts:",
    ]
    lines.extend(f"  {level}: {result.level_counts[level]}" for level in LEVELS)
    lines.append(f"Matched records: {len(result.records)}")

    if result.records:
        lines.extend(_format_record(record) for record in result.records)
    else:
        lines.append("(none)")

    return "\n".join(lines) + "\n"


def _format_record(record: LogRecord) -> str:
    return f"{record.timestamp} {record.level} {record.module} - {record.message}"
