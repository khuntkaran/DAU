"""One error shape for every failure: `{"error": {"code", "message", "details"}}`."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.app.schemas import ErrorResponse


class ApiError(Exception):
    def __init__(
        self, status: int, code: str, message: str, details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details


def not_implemented() -> ApiError:
    return ApiError(
        501, "not_implemented", "This endpoint is part of the contract but not built yet."
    )


def _body(code: str, message: str, details: object = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details}}


async def _api_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ApiError)  # noqa: S101
    return JSONResponse(_body(exc.code, exc.message, exc.details), status_code=exc.status)


async def _http_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)  # noqa: S101
    code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
    return JSONResponse(_body(code, str(exc.detail)), status_code=exc.status_code)


async def _validation_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)  # noqa: S101
    # Pydantic's raw errors carry the input and exception objects; send only what a client can use.
    details = [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
    return JSONResponse(_body("validation_error", "The request is invalid.", details), 422)


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, _api_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(RequestValidationError, _validation_error)


def error_responses(*statuses: int) -> dict[int | str, dict[str, Any]]:
    """OpenAPI entries so generated clients know every error uses `ErrorResponse`.

    422 is always included because FastAPI would otherwise advertise its own validation body.
    """
    return {status: {"model": ErrorResponse} for status in {*statuses, 422}}
