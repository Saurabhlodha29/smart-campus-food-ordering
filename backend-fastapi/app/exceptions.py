"""
ApiException + FastAPI exception handler.

Reproduces the exact JSON error shape from Spring's GlobalExceptionHandler:
  { "timestamp": "...", "status": <int>, "error": "<message>" }

The "timestamp" field is a LocalDateTime.now() string in the Java original —
we match that with a naive datetime ISO string (no timezone suffix).
"""
import datetime

from fastapi import Request
from fastapi.responses import JSONResponse


class ApiException(Exception):
    """
    Equivalent of com.smartcampus.backend.exception.ApiException.
    Carries an HTTP status code + human-readable message.
    Raise this from any service or router; the handler below converts it.
    """

    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _error_body(status: int, message: str) -> dict:  # type: ignore[type-arg]
    return {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "status": status,
        "error": message,
    }


async def api_exception_handler(request: Request, exc: ApiException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.status_code, exc.message),
    )


async def runtime_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all for unhandled RuntimeException equivalents — returns 400
    matching Spring's GlobalExceptionHandler.handleRuntimeException behaviour.
    """
    return JSONResponse(
        status_code=400,
        content=_error_body(400, str(exc)),
    )
