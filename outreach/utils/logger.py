"""
logger.py – Structured, consistent logging for the whole application.

Design rationale
----------------
*  One get_logger() factory rather than module-level basicConfig() calls.
   Each module gets its own named logger (standard Python practice), so log
   output shows exactly which file produced each line.
*  Console output uses colour when the terminal supports it (isatty check)
   without pulling in an extra library.
*  File output (when LOG_FILE is set) writes plain text so it's grep-friendly.
*  We never call logging.basicConfig() — that would affect every logger in
   the process, including third-party libraries.  Instead we configure only
   our own "outreach" namespace.
"""

import logging
import sys
from typing import Optional

# ANSI colour codes — only used when stdout is a real terminal
_COLOURS = {
    "DEBUG": "\033[36m",      # cyan
    "INFO": "\033[32m",       # green
    "WARNING": "\033[33m",    # yellow
    "ERROR": "\033[31m",      # red
    "CRITICAL": "\033[35m",   # magenta
    "RESET": "\033[0m",
}


class ColouredFormatter(logging.Formatter):
    """Adds ANSI colour to the level name when writing to a terminal."""

    def format(self, record: logging.LogRecord) -> str:
        colour = _COLOURS.get(record.levelname, "")
        reset = _COLOURS["RESET"]
        record.levelname = f"{colour}{record.levelname:<8}{reset}"
        return super().format(record)


_PLAIN_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Track whether we've already attached handlers to the root "outreach" logger
_configured = False


def configure_logging(level: str = "INFO", log_file: Optional[str] = None) -> None:
    """
    Call once at application startup (in main.py).
    Subsequent calls are no-ops thanks to the _configured guard.
    """
    global _configured
    if _configured:
        return

    root = logging.getLogger("outreach")
    root.setLevel(getattr(logging, level, logging.INFO))
    root.propagate = False  # Don't bubble up to the root Python logger

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    if sys.stdout.isatty():
        console.setFormatter(ColouredFormatter(_PLAIN_FORMAT, datefmt=_DATE_FORMAT))
    else:
        console.setFormatter(logging.Formatter(_PLAIN_FORMAT, datefmt=_DATE_FORMAT))
    root.addHandler(console)

    # Optional file handler
    if log_file:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(logging.Formatter(_PLAIN_FORMAT, datefmt=_DATE_FORMAT))
        root.addHandler(fh)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Usage in every module::

        from outreach.logger import get_logger
        logger = get_logger(__name__)
    """
    # Ensure the logger lives under the "outreach" namespace so our handler
    # config above applies to it automatically.
    if not name.startswith("outreach"):
        name = f"outreach.{name}"
    return logging.getLogger(name)
