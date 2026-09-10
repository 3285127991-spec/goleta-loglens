from io import StringIO
from contextlib import redirect_stderr, redirect_stdout
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from loglens.cli import build_parser, main


class CliTests(TestCase):
    def test_analyze_text_output(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "app.log"
            path.write_text(
                "2026-09-10 14:20:01 INFO auth - user login succeeded\n",
                encoding="utf-8",
            )
            stdout = StringIO()
            stderr = StringIO()
            args = build_parser().parse_args(["analyze", str(path)])

            exit_code = args.command(args, stdout=stdout, stderr=stderr)

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertIn("Valid log lines: 1", stdout.getvalue())
        self.assertIn("INFO: 1", stdout.getvalue())

    def test_analyze_json_output_with_filters(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "app.log"
            path.write_text(
                "\n".join(
                    [
                        "2026-09-10 14:20:01 INFO auth - user login succeeded",
                        "2026-09-10 14:20:05 ERROR database - connection timeout",
                    ]
                ),
                encoding="utf-8",
            )
            stdout = StringIO()
            stderr = StringIO()
            args = build_parser().parse_args(
                [
                    "analyze",
                    str(path),
                    "--level",
                    "error",
                    "--contains",
                    "TIMEOUT",
                    "--format",
                    "json",
                ]
            )

            exit_code = args.command(args, stdout=stdout, stderr=stderr)

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(payload["valid_lines"], 2)
        self.assertEqual(payload["level_counts"]["ERROR"], 1)
        self.assertEqual(len(payload["records"]), 1)
        self.assertEqual(payload["records"][0]["module"], "database")

    def test_missing_file_returns_nonzero_without_traceback(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        args = build_parser().parse_args(["analyze", "does-not-exist.log"])

        exit_code = args.command(args, stdout=stdout, stderr=stderr)

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("error: Log file not found", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_time_range_and_module_filters_json_output(self) -> None:
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
            stdout = StringIO()
            stderr = StringIO()
            args = build_parser().parse_args(
                [
                    "analyze",
                    str(path),
                    "--module",
                    "database",
                    "--since",
                    "2026-09-10 14:20:05",
                    "--until",
                    "2026-09-10 14:20:05",
                    "--format",
                    "json",
                ]
            )

            exit_code = args.command(args, stdout=stdout, stderr=stderr)

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(payload["valid_lines"], 3)
        self.assertEqual(len(payload["records"]), 1)
        self.assertEqual(payload["records"][0]["module"], "database")

    def test_no_matching_records_returns_success(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "app.log"
            path.write_text(
                "2026-09-10 14:20:01 INFO auth - user login succeeded\n",
                encoding="utf-8",
            )
            stdout = StringIO()
            stderr = StringIO()
            args = build_parser().parse_args(["analyze", str(path), "--module", "missing"])

            exit_code = args.command(args, stdout=stdout, stderr=stderr)

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertIn("Matched records: 0", stdout.getvalue())
        self.assertIn("(none)", stdout.getvalue())

    def test_start_after_end_returns_usage_error(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        args = build_parser().parse_args(
            [
                "analyze",
                "sample.log",
                "--since",
                "2026-09-10 14:20:06",
                "--until",
                "2026-09-10 14:20:05",
            ]
        )

        exit_code = args.command(args, stdout=stdout, stderr=stderr)

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("--since must be earlier than or equal to --until", stderr.getvalue())

    def test_since_and_until_reject_timestamps_missing_zero_padding(self) -> None:
        invalid_values = [
            "2026-9-10 14:20:05",
            "2026-09-1 14:20:05",
            "2026-09-10 4:20:05",
            "2026-09-10 14:2:05",
            "2026-09-10 14:20:5",
        ]

        for option in ("--since", "--until"):
            for value in invalid_values:
                with self.subTest(option=option, value=value):
                    stdout = StringIO()
                    stderr = StringIO()

                    with redirect_stdout(stdout), redirect_stderr(stderr):
                        with self.assertRaises(SystemExit) as context:
                            main(["analyze", "sample.log", option, value])

                    self.assertEqual(context.exception.code, 2)
                    self.assertEqual(stdout.getvalue(), "")
                    self.assertIn(f"argument {option}: invalid timestamp", stderr.getvalue())
                    self.assertNotIn("Valid log lines:", stdout.getvalue())
                    self.assertNotIn("Traceback", stderr.getvalue())

    def test_since_and_until_reject_nonexistent_dates(self) -> None:
        for option in ("--since", "--until"):
            with self.subTest(option=option):
                stdout = StringIO()
                stderr = StringIO()

                with redirect_stdout(stdout), redirect_stderr(stderr):
                    with self.assertRaises(SystemExit) as context:
                        main(["analyze", "sample.log", option, "2026-02-30 14:20:05"])

                self.assertEqual(context.exception.code, 2)
                self.assertEqual(stdout.getvalue(), "")
                self.assertIn(f"argument {option}: invalid timestamp", stderr.getvalue())
                self.assertNotIn("Traceback", stderr.getvalue())

    def test_correctly_padded_single_sided_time_filters_are_accepted(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        args = build_parser().parse_args(
            ["analyze", "sample.log", "--until", "2026-09-10 14:20:05"]
        )

        exit_code = args.command(args, stdout=stdout, stderr=stderr)

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertIn("Valid log lines: 5", stdout.getvalue())
        self.assertIn("Matched records: 3", stdout.getvalue())

    def test_strict_mode_returns_usage_error_without_partial_report(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        args = build_parser().parse_args(["analyze", "sample.log", "--strict"])

        exit_code = args.command(args, stdout=stdout, stderr=stderr)

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("error: Invalid log line at", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())
