from typing import Any

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from social_downloader.api.schemas import (
    ApiResponse,
    AudioInfo,
    ErrorContext,
    ErrorInfo,
    ErrorResponse,
    FileMetadata,
    LocalProcessingResponse,
    OutputInfo,
    PickerItem,
    PickerResponse,
    RedirectResponse,
    TunnelResponse,
)

# What the client receives: camelCase keys, None fields left out.
# Shapes mirror cobalt's createResponse in api/src/processing/request.js.
DUMP_CASES = [
    pytest.param(
        RedirectResponse(url="https://cdn.example/v.mp4", filename="v.mp4"),
        {"status": "redirect", "url": "https://cdn.example/v.mp4", "filename": "v.mp4"},
        id="redirect",
    ),
    pytest.param(
        TunnelResponse(url="https://api.example/tunnel?id=1", filename="v.mp4"),
        {
            "status": "tunnel",
            "url": "https://api.example/tunnel?id=1",
            "filename": "v.mp4",
        },
        id="tunnel",
    ),
    pytest.param(
        PickerResponse(picker=[PickerItem(type="photo", url="https://i/1.jpg")]),
        {"status": "picker", "picker": [{"type": "photo", "url": "https://i/1.jpg"}]},
        id="picker minimal",
    ),
    pytest.param(
        PickerResponse(
            picker=[
                PickerItem(type="video", url="https://v/1.mp4", thumb="https://t/1"),
                PickerItem(type="gif", url="https://v/2.mp4"),
            ],
            audio="https://a/bg.mp3",
            audio_filename="bg.mp3",
        ),
        {
            "status": "picker",
            "picker": [
                {"type": "video", "url": "https://v/1.mp4", "thumb": "https://t/1"},
                {"type": "gif", "url": "https://v/2.mp4"},
            ],
            "audio": "https://a/bg.mp3",
            "audioFilename": "bg.mp3",
        },
        id="picker with audio",
    ),
    pytest.param(
        LocalProcessingResponse(
            type="merge",
            service="youtube",
            tunnel=["https://api/t?id=1", "https://api/t?id=2"],
            output=OutputInfo(
                type="video/mp4",
                filename="v.mp4",
                metadata=FileMetadata(title="t", album_artist="a"),
                subtitles=True,
            ),
            audio=AudioInfo(
                copy=True, format="m4a", bitrate="128", cover=True, crop_cover=True
            ),
            isHLS=False,
        ),
        {
            "status": "local-processing",
            "type": "merge",
            "service": "youtube",
            "tunnel": ["https://api/t?id=1", "https://api/t?id=2"],
            "output": {
                "type": "video/mp4",
                "filename": "v.mp4",
                # cobalt's metadata keys are NOT camelCase: album_artist stays.
                "metadata": {"title": "t", "album_artist": "a"},
                "subtitles": True,
            },
            "audio": {
                "copy": True,
                "format": "m4a",
                "bitrate": "128",
                "cover": True,
                "cropCover": True,
            },
            "isHLS": False,
        },
        id="local-processing full",
    ),
    pytest.param(
        LocalProcessingResponse(
            type="remux",
            service="twitter",
            tunnel=["https://api/t?id=1"],
            output=OutputInfo(type="video/mp4", filename="v.mp4"),
        ),
        {
            "status": "local-processing",
            "type": "remux",
            "service": "twitter",
            "tunnel": ["https://api/t?id=1"],
            "output": {"type": "video/mp4", "filename": "v.mp4"},
        },
        id="local-processing no audio",
    ),
    pytest.param(
        ErrorResponse(error=ErrorInfo(code="error.api.link.invalid")),
        {"status": "error", "error": {"code": "error.api.link.invalid"}},
        id="error minimal",
    ),
    pytest.param(
        ErrorResponse(
            error=ErrorInfo(
                code="error.api.content.too_long",
                context=ErrorContext(service="youtube", limit=10800),
            )
        ),
        {
            "status": "error",
            "error": {
                "code": "error.api.content.too_long",
                "context": {"service": "youtube", "limit": 10800},
            },
        },
        id="error with context",
    ),
    pytest.param(
        ErrorResponse(
            error=ErrorInfo(code="error.api.fetch.critical.core"), critical=True
        ),
        {
            "status": "error",
            "error": {"code": "error.api.fetch.critical.core"},
            "critical": True,
        },
        id="critical error",
    ),
]


@pytest.mark.parametrize(("response", "expected"), DUMP_CASES)
def test_dump(response: BaseModel, expected: dict[str, Any]) -> None:
    assert response.model_dump(exclude_none=True) == expected


def test_python_names_work_in_constructor() -> None:
    # Without validate_by_name=True, audio_filename would be silently dropped.
    response = PickerResponse(picker=[], audio_filename="bg.mp3")
    assert response.audio_filename == "bg.mp3"


API_RESPONSE: TypeAdapter[ApiResponse] = TypeAdapter(ApiResponse)

# (raw dict, class the discriminator must pick)
DISCRIMINATOR_CASES = [
    pytest.param(
        {"status": "redirect", "url": "u", "filename": "f"},
        RedirectResponse,
        id="redirect",
    ),
    pytest.param(
        {"status": "tunnel", "url": "u", "filename": "f"},
        TunnelResponse,
        id="tunnel",
    ),
    pytest.param({"status": "picker", "picker": []}, PickerResponse, id="picker"),
    pytest.param(
        {
            "status": "local-processing",
            "type": "mute",
            "service": "twitter",
            "tunnel": [],
            "output": {"type": "video/mp4", "filename": "v.mp4"},
        },
        LocalProcessingResponse,
        id="local-processing",
    ),
    pytest.param(
        {"status": "error", "error": {"code": "error.api.link.invalid"}},
        ErrorResponse,
        id="error",
    ),
]


@pytest.mark.parametrize(("raw", "expected_cls"), DISCRIMINATOR_CASES)
def test_discriminator_picks_class(raw: dict[str, Any], expected_cls: type) -> None:
    assert type(API_RESPONSE.validate_python(raw)) is expected_cls


def test_unknown_status_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        API_RESPONSE.validate_python({"status": "nope"})
    assert exc_info.value.errors()[0]["type"] == "union_tag_invalid"
