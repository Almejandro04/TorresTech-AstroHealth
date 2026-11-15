"""Every error leaves the API as `{error: {code, message, details}, meta}`."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.models.responses import meta
from app.models.validation import (
    AstronautNotFoundError,
    FieldIssue,
    RecordValidationError,
    issues_from_errors,
)

logger = logging.getLogger("astrohealth.api")

VALIDATION_MESSAGE = "Request validation failed."

# Codes for HTTP errors that are not about a record. A missing route is
# NOT_FOUND, never ASTRONAUT_NOT_FOUND.
_HTTP_CODES = {
    404: ("NOT_FOUND", "The requested resource was not found."),
    405: ("METHOD_NOT_ALLOWED", "The method is not allowed for this resource."),
}


class ReadingConflictError(Exception):
    """The reading key already exists with different values or provenance."""


def error_response(
    status: int,
    code: str,
    message: str,
    details: list[FieldIssue] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body = {
        "error": {"code": code, "message": message, "details": details or []},
        "meta": meta().model_dump(),
    }
    return JSONResponse(body, status_code=status, headers=headers)


def install_error_handling(app: FastAPI) -> None:
    @app.middleware("http")
    async def internal_errors(request: Request, call_next):
        # Registered before CORS so that a 500 still carries CORS headers and
        # the browser can read the error envelope.
        try:
            return await call_next(request)
        except Exception:
            logger.exception("Unhandled error on %s %s", request.method, request.url.path)
            return error_response(500, "INTERNAL_ERROR", "Internal server error.")

    @app.exception_handler(AstronautNotFoundError)
    async def astronaut_not_found(request: Request, error: AstronautNotFoundError):
        return error_response(404, "ASTRONAUT_NOT_FOUND", str(error))

    @app.exception_handler(ReadingConflictError)
    async def reading_conflict(request: Request, error: ReadingConflictError):
        return error_response(
            409,
            "READING_CONFLICT",
            "A different observation already exists for this reading key.",
        )

    @app.exception_handler(RecordValidationError)
    async def record_invalid(request: Request, error: RecordValidationError):
        return error_response(422, "VALIDATION_ERROR", VALIDATION_MESSAGE, error.details)

    @app.exception_handler(RequestValidationError)
    async def request_invalid(request: Request, error: RequestValidationError):
        return error_response(
            422, "VALIDATION_ERROR", VALIDATION_MESSAGE, issues_from_errors(error.errors())
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, error: StarletteHTTPException):
        code, message = _HTTP_CODES.get(
            error.status_code, ("HTTP_ERROR", "The request could not be completed.")
        )
        return error_response(error.status_code, code, message, headers=error.headers)
