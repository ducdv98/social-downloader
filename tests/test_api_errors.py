from typing import Any

import pytest
from pydantic import ValidationError

from social_downloader.api.errors import (
    ApiErrorCode,
    critical_response,
    error_response,
    from_validation_error,
)
from social_downloader.api.schemas import ApiRequest
from social_downloader.domain.errors import ErrorCode

URL = "https://twitter.com/u/status/1"

# (code, context, expected HTTP status, expected JSON body)
# cobalt: fail() -> createResponse("error", ...) -> status 400, code prefixed
# with "error.api." (api/src/core/api.js, processing/request.js).
ERROR_CASES = [
    pytest.param(
        ErrorCode.LINK_INVALID,
        None,
        400,
        {"status": "error", "error": {"code": "error.api.link.invalid"}},
        id="domain code",
    ),
    pytest.param(
        ErrorCode.LINK_UNSUPPORTED,
        {"service": "twitter"},
        400,
        {
            "status": "error",
            "error": {
                "code": "error.api.link.unsupported",
                "context": {"service": "twitter"},
            },
        },
        id="domain code with context",
    ),
    pytest.param(
        ErrorCode.SERVICE_DISABLED,
        {},
        400,
        {"status": "error", "error": {"code": "error.api.service.disabled"}},
        id="empty context left out",
    ),
    pytest.param(
        ApiErrorCode.INVALID_BODY,
        None,
        400,
        {"status": "error", "error": {"code": "error.api.invalid_body"}},
        id="api code",
    ),
    pytest.param(
        ApiErrorCode.LINK_MISSING,
        None,
        400,
        {"status": "error", "error": {"code": "error.api.link.missing"}},
        id="link missing",
    ),
    pytest.param(
        ApiErrorCode.GENERIC,
        None,
        400,
        {"status": "error", "error": {"code": "error.api.generic"}},
        id="generic",
    ),
]


@pytest.mark.parametrize(("code", "context", "status", "expected"), ERROR_CASES)
def test_error_response(
    code: ErrorCode | ApiErrorCode,
    context: dict[str, str] | None,
    status: int,
    expected: dict[str, Any],
) -> None:
    actual_status, body = error_response(code, context)
    assert actual_status == status
    assert body.model_dump(exclude_none=True) == expected


def test_critical_response_default() -> None:
    status, body = critical_response()
    assert status == 500
    assert body.model_dump(exclude_none=True) == {
        "status": "error",
        "error": {"code": "error.api.fetch.critical.core"},
        "critical": True,
    }


def test_critical_response_custom_code() -> None:
    status, body = critical_response(ApiErrorCode.GENERIC)
    assert status == 500
    assert body.error.code == "error.api.generic"
    assert body.critical is True


# (request body, expected error code)
# cobalt checks `if (!request.url)` BEFORE the schema, so a missing or falsy
# url gives link.missing even when other keys are also wrong.
VALIDATION_CASES = [
    pytest.param({}, "error.api.link.missing", id="no url"),
    pytest.param(
        {"downloadMode": "audio"},
        "error.api.link.missing",
        id="no url, other keys present",
    ),
    pytest.param({"url": ""}, "error.api.link.missing", id="empty url"),
    pytest.param({"url": None}, "error.api.link.missing", id="null url"),
    pytest.param({"url": False}, "error.api.link.missing", id="false url"),
    pytest.param({"url": 0}, "error.api.link.missing", id="zero url"),
    pytest.param(
        {"url": "", "foo": 1}, "error.api.link.missing", id="link.missing wins"
    ),
    pytest.param({"url": 123}, "error.api.invalid_body", id="url not str"),
    pytest.param({"url": URL, "foo": 1}, "error.api.invalid_body", id="unknown key"),
    pytest.param(
        {"url": URL, "convertGif": "true"},
        "error.api.invalid_body",
        id="bad bool",
    ),
    pytest.param(
        {"url": URL, "videoQuality": "1081"},
        "error.api.invalid_body",
        id="bad option",
    ),
]


@pytest.mark.parametrize(("body", "expected_code"), VALIDATION_CASES)
def test_from_validation_error(body: dict[str, Any], expected_code: str) -> None:
    with pytest.raises(ValidationError) as exc_info:
        ApiRequest.model_validate(body)
    status, response = from_validation_error(exc_info.value)
    assert status == 400
    assert response.error.code == expected_code
    assert response.error.context is None
