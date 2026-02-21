"""
core/logging_config.py
======================
Structured logging configuration for MadridHousingScanner.
Uses ``structlog`` for machine-readable JSON logs in production
and human-friendly colored output in development.
"""

from __future__ import annotations

import logging
import sys
from typing import Literal

import structlog


# ---------------------------------------------------------------------------
# Public helper
# ---------------------------------------------------------------------------

def configure_logging(
    level: str = "INFO",
    fmt: Literal["json", "console"] = "json",
) -> None:
    """
    Configure stdlib logging + structlog processors.

    Call this once at application startup (e.g. in main.py or the pipeline
    entry points).

    Parameters
    ----------
    level:
        Log level string: ``"DEBUG"``, ``"INFO"``, ``"WARNING"``, ``"ERROR"``.
    fmt:
        ``"json"`` for structured JSON (production / CI),
        ``"console"`` for colored human output (development).
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # ── stdlib handler ───────────────────────────────────────────────────────
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers = [handler]

    # ── shared processors ────────────────────────────────────────────────────
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if fmt == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Return a bound structlog logger for the given module name.

    Usage::

        from core.logging_config import get_logger
        log = get_logger(__name__)
        log.info("pipeline_started", source="idealista", pages=5)
    """
    return structlog.get_logger(name)
