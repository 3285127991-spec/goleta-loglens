from unittest import TestCase

from loglens.parser import parse_log_line, parse_log_line_detailed


class ParseLogLineTests(TestCase):
    def test_parses_valid_line(self) -> None:
        record = parse_log_line("2026-09-10 14:20:01 INFO auth - user login succeeded")

        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(record.timestamp, "2026-09-10 14:20:01")
        self.assertEqual(record.level, "INFO")
        self.assertEqual(record.module, "auth")
        self.assertEqual(record.message, "user login succeeded")

    def test_rejects_invalid_timestamp(self) -> None:
        record = parse_log_line("2026-09-10 14:20:99 INFO auth - impossible time")

        self.assertIsNone(record)

    def test_rejects_unsupported_level(self) -> None:
        record = parse_log_line("2026-09-10 14:20:01 NOTICE auth - noisy event")

        self.assertIsNone(record)

    def test_rejects_malformed_line(self) -> None:
        record = parse_log_line("this is not a log line")

        self.assertIsNone(record)

    def test_reports_rejection_reason(self) -> None:
        outcome = parse_log_line_detailed("2026-09-10 14:20:01 NOTICE auth - noisy event")

        self.assertIsNone(outcome.record)
        self.assertIn("unsupported log level", outcome.error or "")
