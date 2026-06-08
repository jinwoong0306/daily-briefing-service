from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: list[dict] | None = None,
) -> JSONResponse:
    payload: dict = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
        },
    }
    if details:
        payload["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=payload)


def _status_to_error_code(status_code: int) -> str:
    mapping = {
        status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
        status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
        status.HTTP_403_FORBIDDEN: "FORBIDDEN",
        status.HTTP_404_NOT_FOUND: "NOT_FOUND",
        status.HTTP_409_CONFLICT: "CONFLICT",
        status.HTTP_429_TOO_MANY_REQUESTS: "TOO_MANY_REQUESTS",
        status.HTTP_422_UNPROCESSABLE_ENTITY: "VALIDATION_ERROR",
    }
    return mapping.get(status_code, "REQUEST_ERROR")


async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return _error_response(
        status_code=exc.status_code,
        code=_status_to_error_code(exc.status_code),
        message=message,
    )


async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {
            "loc": ".".join(str(part) for part in error.get("loc", [])),
            "msg": error.get("msg", "Invalid value"),
            "type": error.get("type", "value_error"),
        }
        for error in exc.errors()
    ]
    return _error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="VALIDATION_ERROR",
        message="Validation failed",
        details=details,
    )


async def unhandled_exception_handler(_: Request, __: Exception) -> JSONResponse:
    return _error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_ERROR",
        message="Internal server error",
    )
