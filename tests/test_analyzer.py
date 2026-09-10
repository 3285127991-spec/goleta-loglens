from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from datetime import datetime

from loglens.analyzer import LogFileError, StrictModeError, analyze_file


class AnalyzeFileTests(TestCase):
    def test_counts_valid_invalid_and_levels(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "app.log"
            path.write_text(
                "\n".join(
                    [
                        "2026-09-10 14:20:01 INFO auth - user login succeeded",
                        "",
                        "2026-09-10 14:20:02 DEBUG auth - checking session cache",
                        "bad line",
                        "2026-09-10 14:20:05 ERROR database - connection timeout",
                    ]
                ),
                encoding="utf-8",
            )

            result = analyze_file(path)

        self.assertEqual(result.valid_lines, 3)
        self.assertEqual(result.invalid_lines, 1)
        self.assertEqual(result.level_counts["DEBUG"], 1)
        self.assertEqual(result.level_counts["INFO"], 1)
        self.assertEqual(result.level_counts["ERROR"], 1)
        self.assertEqual(result.level_counts["WARNING"], 0)
        self.assertEqual(len(result.records), 3)

    def test_filters_records_without_changing_counts(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "app.log"
            path.write_text(
                "\n".join(
                    [
                        "2026-09-10 14:20:01 INFO auth - user login succeeded",
                        "2026-09-10 14:20:05 ERROR database - connection timeout",
                        "2026-09-10 14:21:10 WARNING api - connection was slow",
                    ]
                ),
                encoding="utf-8",
            )

            result = analyze_file(path, levels=["ERROR", "WARNING"], contains="CONNECTION")

        self.assertEqual(result.valid_lines, 3)
        self.assertEqual(result.invalid_lines, 0)
        self.assertEqual([record.level for record in result.records], ["ERROR", "WARNING"])

    def test_missing_file_raises_user_facing_error(self) -> None:
        with self.assertRaises(LogFileError):
            analyze_file(Path("does-not-exist.log"))

    def test_filters_by_inclusive_time_range_and_module(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "app.log"
            path.write_text(
                "\n".join(
                    [
                        "2026-09-10 14:20:01 INFO auth - user login succeeded",
                        "2026-09-10 14:20:05 ERROR database - connection timeout",
                        "2026-09-10 14:21:10 WARNING api - connection was slow",
                        "2026-09-10 14:22:00 ERROR worker - retry exhausted",
                    ]
                ),
                encoding="utf-8",
            )

            result = analyze_file(
                path,
                modules=["database", "api"],
                since=datetime(2026, 9, 10, 14, 20, 5),
                until=datetime(2026, 9, 10, 14, 21, 10),
            )

        self.assertEqual(result.valid_lines, 4)
        self.assertEqual([record.module for record in result.records], ["database", "api"])

    def test_module_filter_is_case_sensitive_full_match(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "app.log"
            path.write_text(
                "\n".join(
                    [
                        "2026-09-10 14:20:01 INFO auth - lower module",
                        "2026-09-10 14:20:02 INFO Auth - mixed module",
                        "2026-09-10 14:20:03 INFO auth.api - dotted module",
                    ]
                ),
                encoding="utf-8",
            )

            result = analyze_file(path, modules=["auth"])

        self.assertEqual([record.message for record in result.records], ["lower module"])

    def test_strict_mode_stops_on_first_invalid_non_empty_line_with_file_line_number(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "app.log"
            path.write_text(
                "\n".join(
                    [
                        "2026-09-10 14:20:01 INFO auth - user login succeeded",
                        "",
                        "bad line",
                        "2026-09-10 14:20:05 ERROR database - connection timeout",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaises(StrictModeError) as context:
                analyze_file(path, levels=["ERROR"], strict=True)

        self.assertEqual(context.exception.line_number, 3)
        self.assertIn("expected log format", context.exception.reason)
