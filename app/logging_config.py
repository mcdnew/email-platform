# app/logging_config.py
#
# JSON structured logging for the email platform.
#
# Every log line is a single JSON object:
#   {"timestamp": "2026-03-20T03:12:45.123Z", "level": "INFO",
#    "logger": "app.main", "event": "email_sent",
#    "prospect_id": 42, "to": "bob@example.com", ...}
#
# configure_logging() is called once at app startup. It attaches handlers to
# the "app" package logger so all app.* modules emit structured JSON.
# uvicorn's own loggers are left alone.

import json
import logging
import sys
from datetime import datetime, timezone

# Standard LogRecord attributes to exclude from the JSON payload.
# Everything not in this set (i.e. anything passed via extra={}) is merged in.
_STDLIB_ATTRS = frozenset({
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message", "taskName",
})


class JsonFormatter(logging.Formatter):
    """Emit each log record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }

        # Merge any extra={...} fields passed at the call site.
        for key, value in record.__dict__.items():
            if key not in _STDLIB_ATTRS and not key.startswith("_"):
                payload[key] = value

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging(log_path: str = "error_log.txt", level: str = "INFO") -> None:
    """
    Attach a JSON stdout handler and a JSON file handler to the "app" logger.
    Safe to call multiple times (idempotent — clears existing handlers first).
    """
    fmt = JsonFormatter()

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(fmt)

    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(fmt)

    app_logger = logging.getLogger("app")
    app_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    app_logger.handlers.clear()
    app_logger.addHandler(stream_handler)
    app_logger.addHandler(file_handler)
    app_logger.propagate = False  # don't double-log through uvicorn's root handler
