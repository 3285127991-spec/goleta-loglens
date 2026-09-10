"""Command line interface for LogLens."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import re
import sys
from typing import Sequence, TextIO

from .analyzer import LogFileError, StrictModeError, analyze_file
from .formatter import format_result
from .models import LEVELS


TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.command(args, stdout=sys.stdout, stderr=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="loglens",
        description="Analyze local log files.",
    )
    subparsers = parser.add_subparsers(dest="command_name", required=True)

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze a log file.",
        description="Analyze a log file.",
    )
    analyze_parser.add_argument("log_file", type=Path, help="Path to the log file.")
    analyze_parser.add_argument(
        "--level",
        dest="levels",
        action="append",
        type=_level_arg,
        help="Filter matched records by level. Can be repeated.",
    )
    analyze_parser.add_argument(
        "--contains",
        help="Filter matched records by case-insensitive message keyword.",
    )
    analyze_parser.add_argument(
        "--since",
        type=_timestamp_arg,
        help='Filter matched records at or after this timestamp: "YYYY-MM-DD HH:MM:SS".',
    )
    analyze_parser.add_argument(
        "--until",
        type=_timestamp_arg,
        help='Filter matched records at or before this timestamp: "YYYY-MM-DD HH:MM:SS".',
    )
    analyze_parser.add_argument(
        "--module",
        dest="modules",
        action="append",
        help="Filter matched records by exact module name. Can be repeated.",
    )
    analyze_parser.add_argument(
        "--strict",
        action="store_true",
        help="Stop at the first invalid non-empty log line.",
    )
    analyze_parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format. Defaults to text.",
    )
    analyze_parser.set_defaults(command=_run_analyze)
    return parser


def _run_analyze(args: argparse.Namespace, *, stdout: TextIO, stderr: TextIO) -> int:
    if args.since is not None and args.until is not None and args.since > args.until:
        print("error: --since must be earlier than or equal to --until", file=stderr)
        return 2

    try:
        result = analyze_file(
            args.log_file,
            levels=args.levels,
            contains=args.contains,
            modules=args.modules,
            since=args.since,
            until=args.until,
            strict=args.strict,
        )
    except LogFileError as exc:
        print(f"error: {exc}", file=stderr)
        return 1
    except StrictModeError as exc:
        print(f"error: {exc}", file=stderr)
        return 2

    stdout.write(format_result(result, args.format))
    return 0


def _level_arg(value: str) -> str:
    level = value.upper()
    if level not in LEVELS:
        allowed = ", ".join(LEVELS)
        raise argparse.ArgumentTypeError(
            f"unsupported log level '{value}'. Allowed levels: {allowed}"
        )
    return level


def _timestamp_arg(value: str) -> datetime:
    if TIMESTAMP_RE.match(value) is None:
        raise argparse.ArgumentTypeError(
            f"invalid timestamp '{value}'. Expected format: YYYY-MM-DD HH:MM:SS"
        )
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"invalid timestamp '{value}'. Expected format: YYYY-MM-DD HH:MM:SS"
        ) from exc
