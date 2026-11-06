"""Logging that Cloud Error Reporting understands.

On Cloud Run (K_SERVICE is set) every record is one JSON line on stdout with a
`severity`; errors with a traceback also carry Error Reporting's `@type`, the stack trace
and the service/revision, so they are grouped and alerted on without a client library.
Locally, plain text. Also catches the two kinds of failure that never reach a response:
unhandled request errors and exceptions in background asyncio tasks (the hearing's
coaching bug was one).
"""

import asyncio
import json
import logging
import os
import sys
import traceback

REPORTED_ERROR = (
    "type.googleapis.com/google.devtools.clouderrorreporting.v1beta1.ReportedErrorEvent"
)


class CloudRunFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        if record.exc_info:
            # Error Reporting reads the traceback from the message itself.
            entry["message"] += "\n" + "".join(traceback.format_exception(*record.exc_info))
            if record.levelno >= logging.ERROR:
                entry["@type"] = REPORTED_ERROR
                entry["serviceContext"] = {
                    "service": os.environ.get("K_SERVICE", "sombrero"),
                    "version": os.environ.get("K_REVISION", "local"),
                }
        return json.dumps(entry, default=str)


def setup() -> None:
    handler = logging.StreamHandler(sys.stdout)
    if os.environ.get("K_SERVICE"):
        handler.setFormatter(CloudRunFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    # Uvicorn installs its own text handlers; route its records through ours instead.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers = []
        lg.propagate = True


def log_task_exception(loop: asyncio.AbstractEventLoop, context: dict) -> None:
    """Event-loop handler: background task failures become ERROR records, not stderr noise."""
    exc = context.get("exception")
    logging.getLogger("kavach.tasks").error(
        context.get("message", "background task failed"),
        exc_info=(type(exc), exc, exc.__traceback__) if exc else None,
    )
