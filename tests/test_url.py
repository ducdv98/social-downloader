import pytest

from social_downloader.domain.errors import ErrorCode, ExtractError
from social_downloader.domain.url import (
    SERVICES,
    Extracted,
    alias_url,
    clean_url,
    compile_pattern,
    extract,
    get_host_if_valid,
)

# (input, expected). Rows with expected == input must stay unchanged.
ALIAS_CASES = [
    pytest.param(
        "https://x.com/u/status/1",
        "https://twitter.com/u/status/1",
        id="x.com",
    ),
    pytest.param(
        "https://x.com/u/status/1?post_id=5",
        "https://twitter.com/u/status/1?post_id=5",
        id="x.com keeps query",
    ),
    pytest.param(
        "https://vxtwitter.com/u/status/1",
        "https://twitter.com/u/status/1",
        id="vxtwitter",
    ),
    pytest.param(
        "https://fixvx.com/u/status/1",
        "https://twitter.com/u/status/1",
        id="fixvx",
    ),
    pytest.param(
        "https://youtu.be/dQw4w9WgXcQ",
        "https://youtube.com/watch?v=dQw4w9WgXcQ",
        id="youtu.be",
    ),
    pytest.param(
        "https://youtu.be/dQw4w9WgXcQ//junk//",
        "https://youtube.com/watch?v=dQw4w9WgXcQ",
        id="youtu.be only first segment",
    ),
    pytest.param(
        "https://youtube.com/shorts/abc123",
        "https://youtube.com/watch?v=abc123",
        id="shorts",
    ),
    pytest.param(
        "https://www.youtube.com/shorts/abc123",
        "https://youtube.com/watch?v=abc123",
        id="shorts www",
    ),
    pytest.param(
        "https://m.youtube.com/live/abc123",
        "https://youtube.com/watch?v=abc123",
        id="live mobile",
    ),
    # Must stay unchanged
    pytest.param(
        "https://youtube.com/watch?v=abc123",
        "https://youtube.com/watch?v=abc123",
        id="normal watch link unchanged",
    ),
    pytest.param(
        "https://example.org/x",
        "https://example.org/x",
        id="unknown host unchanged",
    ),
    # Must not crash
    pytest.param("https://youtu.be/", "https://youtu.be/", id="youtu.be no id"),
    pytest.param("https://youtu.be", "https://youtu.be", id="youtu.be no path"),
    pytest.param(
        "https://youtube.com/shorts",
        "https://youtube.com/shorts",
        id="shorts no id",
    ),
    # shorts/live rewrite is youtube-only, other services keep the path
    pytest.param(
        "https://twitter.com/shorts/abc",
        "https://twitter.com/shorts/abc",
        id="twitter user named shorts",
    ),
    pytest.param(
        "https://twitter.com/live/abc",
        "https://twitter.com/live/abc",
        id="twitter user named live",
    ),
    pytest.param("", "", id="empty string"),
    pytest.param(
        "https://music.youtube.com/shorts/abc",
        "https://youtube.com/watch?v=abc",
        id="shorts on music subdomain",
    ),
]


@pytest.mark.parametrize(("url", "expected"), ALIAS_CASES)
def test_alias_url(url: str, expected: str) -> None:
    assert alias_url(url) == expected


CLEAN_CASES = [
    # Whitelisted query param is kept, the rest is dropped
    pytest.param(
        "https://youtube.com/watch?v=ID&list=PL&t=10",
        "https://youtube.com/watch?v=ID",
        id="youtube keeps v only",
    ),
    pytest.param(
        "https://www.youtube.com/watch?v=ID",
        "https://www.youtube.com/watch?v=ID",
        id="youtube www keeps v",
    ),
    pytest.param(
        "https://m.youtube.com/watch?v=ID",
        "https://m.youtube.com/watch?v=ID",
        id="youtube mobile keeps v",
    ),
    pytest.param(
        "https://twitter.com/u/status/1?post_id=5&x=1",
        "https://twitter.com/u/status/1?post_id=5",
        id="twitter keeps post_id only",
    ),
    pytest.param(
        "https://youtube.com/watch?v=a&v=b",
        "https://youtube.com/watch?v=a",
        id="repeated param: first wins",
    ),
    pytest.param(
        "https://youtube.com/watch?v=a%26b",
        "https://youtube.com/watch?v=a%26b",
        id="encoded value survives",
    ),
    # Whitelisted param missing: no query at all
    pytest.param(
        "https://youtube.com/watch?list=PL",
        "https://youtube.com/watch",
        id="youtube without v",
    ),
    # Unknown host: whole query dropped
    pytest.param(
        "https://example.org/a?b=1",
        "https://example.org/a",
        id="unknown host drops query",
    ),
    # Credentials, port, fragment
    pytest.param(
        "https://user:pw@youtube.com:443/watch?v=ID#frag",
        "https://youtube.com/watch?v=ID",
        id="strip credentials, port, fragment",
    ),
    pytest.param(
        "https://example.org/a#top",
        "https://example.org/a",
        id="strip fragment, no query",
    ),
    # Trailing slash
    pytest.param(
        "https://youtube.com/watch/",
        "https://youtube.com/watch",
        id="strip trailing slash",
    ),
    pytest.param(
        "https://youtube.com/",
        "https://youtube.com",
        id="root path becomes empty",
    ),
    pytest.param("", "", id="empty string"),
    # Whitelist is keyed by service, so any valid subdomain keeps its param
    pytest.param(
        "https://music.youtube.com/watch?v=abc&list=x",
        "https://music.youtube.com/watch?v=abc",
        id="music subdomain keeps v",
    ),
    pytest.param(
        "https://mobile.twitter.com/i/bookmarks?post_id=5&t=1",
        "https://mobile.twitter.com/i/bookmarks?post_id=5",
        id="mobile subdomain keeps post_id",
    ),
]


@pytest.mark.parametrize(("url", "expected"), CLEAN_CASES)
def test_clean_url(url: str, expected: str) -> None:
    assert clean_url(url) == expected


# (input, expected service key or None). Input is already aliased + cleaned.
HOST_CASES = [
    # Valid: bare host, www, listed subdomain
    pytest.param("https://youtube.com/watch?v=ID", "youtube", id="youtube bare"),
    pytest.param("https://www.youtube.com/watch?v=ID", "youtube", id="youtube www"),
    pytest.param("https://m.youtube.com/watch?v=ID", "youtube", id="youtube m"),
    pytest.param("https://music.youtube.com/watch?v=ID", "youtube", id="youtube music"),
    pytest.param("https://twitter.com/u/status/1", "twitter", id="twitter bare"),
    pytest.param("https://www.twitter.com/u/status/1", "twitter", id="twitter www"),
    pytest.param(
        "https://mobile.twitter.com/u/status/1", "twitter", id="twitter mobile"
    ),
    pytest.param("https://YouTube.COM/watch?v=ID", "youtube", id="host is lowercased"),
    # Invalid subdomain
    pytest.param("https://evil.youtube.com/watch?v=ID", None, id="unlisted subdomain"),
    pytest.param(
        "https://m.twitter.com/u/status/1", None, id="m not listed for twitter"
    ),
    pytest.param("https://a.www.youtube.com/watch?v=ID", None, id="nested subdomain"),
    # Wrong tld
    pytest.param("https://youtube.ru/watch?v=ID", None, id="wrong tld"),
    pytest.param("https://youtube.co.uk/watch?v=ID", None, id="multi-label suffix"),
    # Unknown service
    pytest.param("https://example.com/video", None, id="unknown sld"),
    pytest.param("https://x.com/u/status/1", None, id="alias not applied yet"),
    # No public suffix / not a domain
    pytest.param("https://localhost/x", None, id="localhost"),
    pytest.param("https://127.0.0.1/x", None, id="ip address"),
    pytest.param("not a url", None, id="garbage"),
    pytest.param("", None, id="empty string"),
]


@pytest.mark.parametrize(("url", "expected"), HOST_CASES)
def test_get_host_if_valid(url: str, expected: str | None) -> None:
    assert get_host_if_valid(url) == expected


# (pattern, path, expected groupdict or None for no match)
PATTERN_CASES = [
    # Matches
    pytest.param(
        ":user/status/:id",
        "jack/status/20",
        {"user": "jack", "id": "20"},
        id="twitter status",
    ),
    pytest.param(
        "watch?v=:id",
        "watch?v=abc",
        {"id": "abc"},
        id="query pattern",
    ),
    pytest.param(
        ":user/status/:id",
        "a.b@c:d~e-f_g/status/1",
        {"user": "a.b@c:d~e-f_g", "id": "1"},
        id="full charset in param",
    ),
    # No match
    pytest.param(
        ":user/status/:id",
        "jack/status/20/x",
        None,
        id="anchored at end",
    ),
    pytest.param(
        "watch?v=:id",
        "watcv=abc",
        None,
        id="? is literal, not regex",
    ),
    pytest.param(
        "embed/:id",
        "embed/",
        None,
        id="param needs 1+ chars",
    ),
    pytest.param(
        ":user/status/:id",
        "a/b/status/1",
        None,
        id="param never crosses /",
    ),
]


@pytest.mark.parametrize(("pattern", "path", "expected"), PATTERN_CASES)
def test_compile_pattern(
    pattern: str, path: str, expected: dict[str, str] | None
) -> None:
    match = compile_pattern(pattern).fullmatch(path)
    assert (None if match is None else match.groupdict()) == expected


# (normalized url, expected Extracted or ExtractError).
# Input is already aliased + cleaned, like cobalt (schema.js normalizes first).
EXTRACT_CASES = [
    # Success
    pytest.param(
        "https://twitter.com/jack/status/20",
        Extracted("twitter", {"user": "jack", "id": "20"}),
        id="twitter status",
    ),
    pytest.param(
        "https://twitter.com/jack/status/20/video/1",
        Extracted("twitter", {"user": "jack", "id": "20", "index": "1"}),
        id="twitter video index",
    ),
    pytest.param(
        "https://twitter.com/i/bookmarks?post_id=20",
        Extracted("twitter", {"id": "20"}),
        id="twitter bookmarks query",
    ),
    pytest.param(
        "https://youtube.com/watch?v=dQw4w9WgXcQ",
        Extracted("youtube", {"id": "dQw4w9WgXcQ"}),
        id="youtube watch",
    ),
    pytest.param(
        "https://music.youtube.com/watch?v=abc",
        Extracted("youtube", {"id": "abc"}),
        id="youtube music subdomain",
    ),
    # Tester limits (service-patterns.js): youtube id <= 11, twitter id < 20
    pytest.param(
        "https://youtube.com/watch?v=" + "a" * 11,
        Extracted("youtube", {"id": "a" * 11}),
        id="youtube id 11 chars ok",
    ),
    pytest.param(
        "https://twitter.com/u/status/" + "1" * 19,
        Extracted("twitter", {"user": "u", "id": "1" * 19}),
        id="twitter id 19 digits ok",
    ),
    # Errors
    pytest.param(
        "https://youtube.com/watch?v=" + "a" * 12,
        ExtractError(ErrorCode.LINK_UNSUPPORTED, {"service": "youtube"}),
        id="youtube id 12 chars rejected",
    ),
    pytest.param(
        "https://twitter.com/u/status/" + "1" * 20,
        ExtractError(ErrorCode.LINK_UNSUPPORTED, {"service": "twitter"}),
        id="twitter id 20 digits rejected",
    ),
    pytest.param(
        "https://example.com/x",
        ExtractError(ErrorCode.LINK_INVALID),
        id="unknown host",
    ),
    pytest.param(
        "https://twitter.com/jack",
        ExtractError(ErrorCode.LINK_UNSUPPORTED, {"service": "twitter"}),
        id="no pattern matches",
    ),
]


@pytest.mark.parametrize(("url", "expected"), EXTRACT_CASES)
def test_extract(url: str, expected: Extracted | ExtractError) -> None:
    assert extract(url) == expected


def test_extract_service_disabled() -> None:
    result = extract("https://twitter.com/jack/status/20", enabled_services=frozenset())
    assert result == ExtractError(ErrorCode.SERVICE_DISABLED)


def test_full_pipeline_music_subdomain() -> None:
    url = "https://music.youtube.com/watch?v=abc&si=x"
    assert extract(clean_url(alias_url(url))) == Extracted("youtube", {"id": "abc"})


# Testers called directly. A missing param must fail, like JS `pattern.id?.length`
# (undefined < 20 is false). `len(p.get("id", ""))` would wrongly pass.
TESTER_CASES = [
    pytest.param("youtube", {"id": "a" * 11}, True, id="youtube at limit"),
    pytest.param("youtube", {"id": "a" * 12}, False, id="youtube over limit"),
    pytest.param("youtube", {}, False, id="youtube missing id"),
    pytest.param("twitter", {"id": "1" * 19}, True, id="twitter at limit"),
    pytest.param("twitter", {"id": "1" * 20}, False, id="twitter over limit"),
    pytest.param("twitter", {}, False, id="twitter missing id"),
]


@pytest.mark.parametrize(("service", "params", "expected"), TESTER_CASES)
def test_service_tester(service: str, params: dict[str, str], expected: bool) -> None:
    assert SERVICES[service].tester(params) is expected
