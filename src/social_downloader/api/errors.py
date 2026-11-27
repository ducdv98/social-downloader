from collections.abc import Mapping
from enum import StrEnum

from pydantic import ValidationError

from social_downloader.api.schemas import ErrorContext, ErrorInfo, ErrorResponse
from social_downloader.domain.errors import ErrorCode

_PREFIX = "error.api."


class ApiErrorCode(StrEnum):
    LINK_MISSING = "link.missing"
    INVALID_BODY = "invalid_body"
    GENERIC = "generic"
    CRITICAL_CORE = "fetch.critical.core"


def error_response(
    code: ApiErrorCode | ErrorCode, context: Mapping[str, str] | None = None
) -> tuple[int, ErrorResponse]:
    response_code = f"{_PREFIX}{code}"
    response_context: ErrorContext | None = None
    if context is not None and len(context) > 0:
        response_context = ErrorContext.model_validate(dict(context))
    return 400, ErrorResponse(
        status="error", error=ErrorInfo(code=response_code, context=response_context)
    )


def critical_response(
    code: ApiErrorCode = ApiErrorCode.CRITICAL_CORE,
) -> tuple[int, ErrorResponse]:
    return 500, ErrorResponse(
        status="error", error=ErrorInfo(code=f"{_PREFIX}{code}"), critical=True
    )


def from_validation_error(exc: ValidationError) -> tuple[int, ErrorResponse]:
    for error in exc.errors():
        if error["loc"] == ("url",) and (
            error["type"] == "missing" or not error["input"]
        ):
            return error_response(ApiErrorCode.LINK_MISSING)
    return error_response(ApiErrorCode.INVALID_BODY)
