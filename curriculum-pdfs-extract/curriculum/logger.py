"""
curriculum/logger.py
--------------------
Initialises a dual-output logger: rotating file handler (logs/ directory) and
optional console output.  All other modules import `get_logger()` from here.

Design choices
--------------
- Uses Python's stdlib `logging` only — no extra dependencies.
- Log filename encodes the run timestamp so parallel runs never clash.
- Maintains a module-level dict of named loggers to avoid duplicate handlers
  when the same logger is requested more than once.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

_loggers: dict[str, logging.Logger] = {}
_log_file_path: Optional[Path] = None


def setup_logging(
    logs_dir: str | Path = "logs",
    verbose: bool = False,
) -> Path:
    """
    Call once at program start.  Creates the logs directory, attaches a
    timestamped FileHandler and (optionally) a StreamHandler to the root
    logger, and returns the path of the log file.
    """
    global _log_file_path

    logs_path = Path(logs_dir)
    logs_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_path / f"parse_{timestamp}.log"
    _log_file_path = log_file

    # Keep root logger at WARNING to silence third-party noise
    # (pdfplumber / pdfminer emit millions of DEBUG tokens at root level).
    root = logging.getLogger()
    root.setLevel(logging.WARNING)

    # Explicitly silence the noisiest third-party loggers
    for noisy in ("pdfminer", "pdfplumber", "pypdfium2", "PIL", "fitz"):
        logging.getLogger(noisy).setLevel(logging.ERROR)

    # Our own logger hierarchy — set to DEBUG always (file captures it all)
    our_root = logging.getLogger("curriculum")
    our_root.setLevel(logging.DEBUG)
    our_root.propagate = False  # don't let it bubble up to root

    # Also capture the "main" logger (used by the CLI entry point)
    main_logger = logging.getLogger("main")
    main_logger.setLevel(logging.DEBUG)
    main_logger.propagate = False

    # File handler — always DEBUG level (for our loggers)
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    our_root.addHandler(fh)
    main_logger.addHandler(fh)

    # Console handler — INFO normally, DEBUG when --verbose.
    # On Windows the default stdout encoding may be cp1252; reconfigure it to
    # UTF-8 so that course names with special characters don't crash the logger.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Python 3.7+
    except AttributeError:
        pass  # non-TextIOWrapper stdout (e.g. redirected to file) — ignore
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG if verbose else logging.INFO)
    ch.setFormatter(
        logging.Formatter(
            fmt="%(levelname)-8s %(message)s",
        )
    )
    our_root.addHandler(ch)
    main_logger.addHandler(ch)

    return log_file


def get_logger(name: str) -> logging.Logger:
    """Return a named child logger (cached)."""
    if name not in _loggers:
        _loggers[name] = logging.getLogger(name)
    return _loggers[name]


def get_log_file_path() -> Optional[Path]:
    """Return the active log file path (None if setup_logging not yet called)."""
    return _log_file_path


# ---------------------------------------------------------------------------
# Convenience helpers used across modules
# ---------------------------------------------------------------------------

def log_unmapped_row(logger: logging.Logger, pdf: str, page: int, raw: dict) -> None:
    """Log a row that could not be fully mapped."""
    logger.warning(
        "UNMAPPED_ROW | pdf=%s page=%d | raw_code=%r raw_name=%r raw_type=%r",
        pdf,
        page,
        raw.get("raw_code"),
        raw.get("raw_name"),
        raw.get("raw_type"),
    )


def log_skip_row(logger: logging.Logger, reason: str, pdf: str, page: int, row: dict) -> None:
    """Log a skipped row (e.g. missing course name)."""
    logger.warning(
        "SKIP_ROW | reason=%s | pdf=%s page=%d | row=%r",
        reason,
        pdf,
        page,
        row,
    )


def log_parse_success(logger: logging.Logger, pdf: str, row_count: int) -> None:
    logger.info("PARSE_OK  | pdf=%s | rows=%d", pdf, row_count)


def log_parse_failure(logger: logging.Logger, pdf: str, error: str) -> None:
    logger.error("PARSE_FAIL | pdf=%s | error=%s", pdf, error)
