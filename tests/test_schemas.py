from typing import Any

import pytest
from pydantic import ValidationError

from social_downloader.api.schemas import ApiRequest

URL = "https://twitter.com/u/status/1"

# Every field's default, keyed by the Python (snake_case) name.
# Mirrors cobalt's api/src/processing/schema.js.
DEFAULTS: dict[str, Any] = {
    "url": URL,
    "audio_bitrate": "128",
    "audio_format": "mp3",
    "download_mode": "auto",
    "filename_style": "basic",
    "youtube_video_codec": "h264",
    "youtube_video_container": "auto",
    "video_quality": "1080",
    "local_processing": "disabled",
    "youtube_dub_lang": None,
    "subtitle_lang": None,
    "disable_metadata": False,
    "allow_h265": False,
    "convert_gif": True,
    "tiktok_full_audio": False,
    "always_proxy": False,
    "youtube_hls": False,
    "youtube_better_audio": False,
}


def test_only_url_is_required_and_defaults_fill_in() -> None:
    request = ApiRequest.model_validate({"url": URL})
    assert request.model_dump() == DEFAULTS


# (camelCase JSON key, value sent, Python attribute that must hold it)
ACCEPT_CASES = [
    # url is NOT normalized by the model; the domain pipeline does that later.
    pytest.param("url", "https://x.com/u/status/1?s=20", "url", id="url kept as-is"),
    pytest.param("audioBitrate", "320", "audio_bitrate", id="audioBitrate"),
    pytest.param("audioBitrate", "8", "audio_bitrate", id="audioBitrate lowest"),
    pytest.param("audioFormat", "opus", "audio_format", id="audioFormat"),
    pytest.param("downloadMode", "audio", "download_mode", id="downloadMode"),
    pytest.param("filenameStyle", "nerdy", "filename_style", id="filenameStyle"),
    pytest.param("youtubeVideoCodec", "av1", "youtube_video_codec", id="codec"),
    pytest.param("youtubeVideoContainer", "mkv", "youtube_video_container", id="ctr"),
    pytest.param("videoQuality", "max", "video_quality", id="videoQuality max"),
    pytest.param("videoQuality", "144", "video_quality", id="videoQuality 144"),
    pytest.param("localProcessing", "forced", "local_processing", id="localProc"),
    pytest.param("youtubeDubLang", "en", "youtube_dub_lang", id="dub 2 chars"),
    pytest.param("subtitleLang", "pt-BR", "subtitle_lang", id="sub with dash"),
    pytest.param("subtitleLang", "12345678", "subtitle_lang", id="sub 8 chars"),
    pytest.param("disableMetadata", True, "disable_metadata", id="disableMetadata"),
    pytest.param("allowH265", True, "allow_h265", id="allowH265"),
    pytest.param("convertGif", False, "convert_gif", id="convertGif off"),
    pytest.param("tiktokFullAudio", True, "tiktok_full_audio", id="tiktokFullAudio"),
    pytest.param("alwaysProxy", True, "always_proxy", id="alwaysProxy"),
    # cobalt spells it HLS, which to_camel can't produce: needs an explicit alias.
    pytest.param("youtubeHLS", True, "youtube_hls", id="youtubeHLS"),
    pytest.param("youtubeBetterAudio", True, "youtube_better_audio", id="betterAudio"),
]


@pytest.mark.parametrize(("key", "value", "attr"), ACCEPT_CASES)
def test_accepts(key: str, value: object, attr: str) -> None:
    body: dict[str, object] = {"url": URL, key: value}
    request = ApiRequest.model_validate(body)
    assert getattr(request, attr) == value


# (body, pydantic error type, error location). The location uses the JSON key.
REJECT_CASES = [
    pytest.param({}, "missing", ("url",), id="no url"),
    pytest.param({"url": ""}, "string_too_short", ("url",), id="empty url"),
    pytest.param({"url": 123}, "string_type", ("url",), id="url not str"),
    pytest.param({"url": None}, "string_type", ("url",), id="url null"),
    # extra="forbid", like cobalt's .strict()
    pytest.param({"url": URL, "foo": 1}, "extra_forbidden", ("foo",), id="unknown key"),
    pytest.param(
        {"url": URL, "audio_bitrate": "128"},
        "extra_forbidden",
        ("audio_bitrate",),
        id="snake_case key",
    ),
    pytest.param(
        {"url": URL, "youtubeHls": True},
        "extra_forbidden",
        ("youtubeHls",),
        id="youtubeHls wrong case",
    ),
    # Literal values
    pytest.param(
        {"url": URL, "audioBitrate": "100"},
        "literal_error",
        ("audioBitrate",),
        id="bitrate not allowed",
    ),
    pytest.param(
        {"url": URL, "audioBitrate": 128},
        "literal_error",
        ("audioBitrate",),
        id="bitrate as number",
    ),
    pytest.param(
        {"url": URL, "videoQuality": "1081"},
        "literal_error",
        ("videoQuality",),
        id="quality not allowed",
    ),
    pytest.param(
        {"url": URL, "downloadMode": "AUDIO"},
        "literal_error",
        ("downloadMode",),
        id="mode is case sensitive",
    ),
    # StrictBool: no coercion, unlike plain bool
    pytest.param(
        {"url": URL, "convertGif": "true"}, "bool_type", ("convertGif",), id="bool str"
    ),
    pytest.param(
        {"url": URL, "convertGif": 1}, "bool_type", ("convertGif",), id="bool 1"
    ),
    pytest.param(
        {"url": URL, "youtubeHLS": "yes"}, "bool_type", ("youtubeHLS",), id="bool yes"
    ),
    # LangCode: 2-8 chars of [0-9a-zA-Z-]
    pytest.param(
        {"url": URL, "subtitleLang": "e"},
        "string_too_short",
        ("subtitleLang",),
        id="lang 1 char",
    ),
    pytest.param(
        {"url": URL, "subtitleLang": "123456789"},
        "string_too_long",
        ("subtitleLang",),
        id="lang 9 chars",
    ),
    pytest.param(
        {"url": URL, "youtubeDubLang": "en_US"},
        "string_pattern_mismatch",
        ("youtubeDubLang",),
        id="lang underscore",
    ),
    pytest.param(
        {"url": URL, "youtubeDubLang": "en US"},
        "string_pattern_mismatch",
        ("youtubeDubLang",),
        id="lang space",
    ),
    pytest.param(
        {"url": URL, "subtitleLang": 5},
        "string_type",
        ("subtitleLang",),
        id="lang not str",
    ),
]


@pytest.mark.parametrize(("body", "error_type", "loc"), REJECT_CASES)
def test_rejects(
    body: dict[str, object], error_type: str, loc: tuple[str, ...]
) -> None:
    with pytest.raises(ValidationError) as exc_info:
        ApiRequest.model_validate(body)
    errors = exc_info.value.errors()
    assert len(errors) == 1
    assert errors[0]["type"] == error_type
    assert errors[0]["loc"] == loc
