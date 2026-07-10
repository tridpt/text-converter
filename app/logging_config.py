"""Logging setup. Supports plain or JSON (structured) output for production."""

from __future__ import annotations

import json
import logging
import sys

from .config import settings

LOGGER_NAME = "text_converter"


class JsonFormatter(logging.Formatter):
    """Render log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Attach any structured extras passed via logger.info(..., extra={...}).
        for key, value in getattr(record, "extra_fields", {}).items():
            payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> logging.Logger:
    handler = logging.StreamHandler(sys.stdout)
    if settings.log_json:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level)
    return logging.getLogger(LOGGER_NAME)


def log(logger: logging.Logger, level: int, message: str, **fields) -> None:
    """Log ``message`` with structured ``fields`` (shown in JSON mode)."""
    logger.log(level, message, extra={"extra_fields": fields})
