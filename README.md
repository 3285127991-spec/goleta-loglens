# LogLens

LogLens is a local Python 3.11 command line tool for analyzing plain-text log
files. It reads a log file, counts valid and invalid lines, summarizes log
levels, and prints records that match optional filters.

The project uses only the Python standard library.

## Installation

Run directly from the project directory:

```powershell
python -m loglens analyze sample.log
```

Optional editable installation:

```powershell
python -m pip install -e .
loglens analyze sample.log
```

## Log Format

Each non-empty log line must match this format:

```text
YYYY-MM-DD HH:MM:SS LEVEL MODULE - MESSAGE
```

Example:

```text
2026-09-10 14:20:01 INFO auth - user login succeeded
2026-09-10 14:20:05 ERROR database - connection timeout
```

Supported levels are:

```text
DEBUG, INFO, WARNING, ERROR, CRITICAL
```

Empty lines are ignored. Non-empty lines that do not match the format, contain
an unsupported level, or contain an invalid timestamp are counted as invalid.

## Usage

```powershell
python -m loglens analyze <log-file-path> [--level LEVEL] [--contains KEYWORD] [--since TIMESTAMP] [--until TIMESTAMP] [--module MODULE] [--strict] [--format text|json]
```

Options:

- `--level LEVEL`: Show only matching records with this level. Can be repeated.
- `--contains KEYWORD`: Show only records whose message contains the keyword,
  case-insensitively.
- `--since TIMESTAMP`: Show only records at or after this timestamp. The format
  is `YYYY-MM-DD HH:MM:SS`.
- `--until TIMESTAMP`: Show only records at or before this timestamp. The format
  is `YYYY-MM-DD HH:MM:SS`.
- `--module MODULE`: Show only records whose module exactly matches this value.
  Module matching is case-sensitive. Can be repeated.
- `--strict`: Stop at the first invalid non-empty log line and report the
  original file line number plus the parse failure reason.
- `--format text|json`: Select output format. Defaults to `text`.

Level counts are computed across all valid non-empty log lines in the file.
Filters only affect the `Matched records` section. Multiple `--level` values are
combined with OR, and multiple `--module` values are combined with OR. Level,
module, keyword, and time range filters are combined with AND.

## Output

Text output contains:

- valid log line count;
- invalid log line count;
- count for each supported level;
- records matching the selected filters.

JSON output contains the same data using these keys:

- `valid_lines`
- `invalid_lines`
- `level_counts`
- `records`

## Limitations

- Input is read as UTF-8 text.
- Only local files are supported.
- No network, database, or third-party service is used.
- The parser expects a single-line log entry per record.
