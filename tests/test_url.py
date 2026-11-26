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
    # Deviation from cobalt: www. and mobile. on alt domains are aliased too.
    pytest.param(
        "https://www.x.com/u/status/1",
        "https://twitter.com/u/status/1",
        id="www.x.com",
    ),
    pytest.param(
        "https://mobile.x.com/u/status/1",
        "https://twitter.com/u/status/1",
        id="mobile.x.com",
    ),
    pytest.param(
        "https://www.vxtwitter.com/u/status/1",
        "https://twitter.com/u/status/1",
        id="www.vxtwitter",
    ),
    pytest.param(
        "https://mobile.fixvx.com/u/status/1",
        "https://twitter.com/u/status/1",
        id="mobile.fixvx",
    ),
    # Any other subdomain must NOT be aliased, or it would skip the
    # subdomain check that api.twitter.com fails.
    pytest.param(
        "https://api.x.com/u/status/1",
        "https://api.x.com/u/status/1",
        id="api.x.com unchanged",
    ),
    pytest.param(
        "https://www.mobile.x.com/u/status/1",
        "https://www.mobile.x.com/u/status/1",
        id="nested subdomain unchanged",
    ),
    pytest.param(
        "https://notx.com/u/status/1",
        "https://notx.com/u/status/1",
        id="lookalike notx.com unchanged",
    ),
    pytest.param(
        "https://x.com.evil.com/u/status/1",
        "https://x.com.evil.com/u/status/1",
        id="x.com as subdomain of other site unchanged",
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
    pytest.param("twitter", {"id": "abc"}, False, id="twitter letters"),
    pytest.param("twitter", {"id": "12a"}, False, id="twitter digits then letter"),
    pytest.param("twitter", {"id": "١٢٣"}, False, id="twitter non-ascii digits"),
    pytest.param("twitter", {"id": "12 3"}, False, id="twitter inner space"),
    pytest.param("twitter", {"id": ""}, False, id="twitter empty id"),
]


@pytest.mark.parametrize(("service", "params", "expected"), TESTER_CASES)
def test_service_tester(service: str, params: dict[str, str], expected: bool) -> None:
    assert SERVICES[service].tester(params) is expected


# Full pipeline: extract(clean_url(alias_url(raw))). Raw links, mostly real ones
# from cobalt's api/src/util/tests/{youtube,twitter}.json.
# Pure layer: a link to a deleted video/tweet still succeeds here; cobalt's
# 400 for those comes from the extractor (network), not the URL pipeline.
def _yt(video_id: str) -> Extracted:
    return Extracted("youtube", {"id": video_id})


def _tw(user: str, tweet_id: str, **extra: str) -> Extracted:
    return Extracted("twitter", {"user": user, "id": tweet_id, **extra})


_INVALID = ExtractError(ErrorCode.LINK_INVALID)
_YT_UNSUPPORTED = ExtractError(ErrorCode.LINK_UNSUPPORTED, {"service": "youtube"})
_TW_UNSUPPORTED = ExtractError(ErrorCode.LINK_UNSUPPORTED, {"service": "twitter"})

PIPELINE_CASES = [
    # --- youtube: real links ---
    pytest.param(
        "https://www.youtube.com/watch?v=vPwaXytZcgI",
        _yt("vPwaXytZcgI"),
        id="yt real watch",
    ),
    pytest.param(
        "https://music.youtube.com/watch?v=5rGTsvZCEdk&feature=share",
        _yt("5rGTsvZCEdk"),
        id="yt real music + feature",
    ),
    pytest.param(
        "https://www.youtube.com/watch?v=t5nC_ucYBrc",
        _yt("t5nC_ucYBrc"),
        id="yt real id with underscore",
    ),
    pytest.param(
        "https://www.youtube.com/shorts/r5FpeOJItbw",
        _yt("r5FpeOJItbw"),
        id="yt real shorts",
    ),
    pytest.param(
        "https://www.youtube.com/live/ENxZS6PUDuI?feature=shared",
        _yt("ENxZS6PUDuI"),
        id="yt real live + feature",
    ),
    pytest.param(
        "https://www.youtube.com/watch?v=hEdzv7D4CbQ",
        _yt("hEdzv7D4CbQ"),
        id="yt real watch 2",
    ),
    pytest.param(
        "https://youtube.com/watch?v=gnjuHYWGEW",
        _yt("gnjuHYWGEW"),
        id="yt real 10-char id (cobalt 400 is network, not pipeline)",
    ),
    # --- youtube: share / short forms ---
    pytest.param(
        "https://youtu.be/dQw4w9WgXcQ",
        _yt("dQw4w9WgXcQ"),
        id="yt youtu.be",
    ),
    pytest.param(
        "https://youtu.be/dQw4w9WgXcQ?si=AbCdEf123",
        _yt("dQw4w9WgXcQ"),
        id="yt youtu.be + si tracking",
    ),
    pytest.param(
        "https://youtu.be/dQw4w9WgXcQ//junk//",
        _yt("dQw4w9WgXcQ"),
        id="yt youtu.be only first segment counts",
    ),
    pytest.param(
        "https://youtube.com/shorts/r5FpeOJItbw?feature=share",
        _yt("r5FpeOJItbw"),
        id="yt shorts + feature",
    ),
    pytest.param(
        "https://m.youtube.com/watch?v=dQw4w9WgXcQ&feature=youtu.be",
        _yt("dQw4w9WgXcQ"),
        id="yt mobile subdomain",
    ),
    pytest.param(
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        _yt("dQw4w9WgXcQ"),
        id="yt embed",
    ),
    pytest.param(
        "https://youtube.com/v/dQw4w9WgXcQ",
        _yt("dQw4w9WgXcQ"),
        id="yt /v/ legacy",
    ),
    pytest.param(
        "https://youtube.com/watch/dQw4w9WgXcQ",
        _yt("dQw4w9WgXcQ"),
        id="yt /watch/ path form",
    ),
    # --- youtube: query / url noise ---
    pytest.param(
        "https://www.youtube.com/watch?feature=share&v=dQw4w9WgXcQ",
        _yt("dQw4w9WgXcQ"),
        id="yt v not first param",
    ),
    pytest.param(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s&list=PLx",
        _yt("dQw4w9WgXcQ"),
        id="yt timestamp + playlist stripped",
    ),
    pytest.param(
        "https://www.youtube.com/watch?v=aaaaaaaaaaa&v=bbbbbbbbbbb",
        _yt("aaaaaaaaaaa"),
        id="yt duplicate v first wins",
    ),
    pytest.param(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ#t=30",
        _yt("dQw4w9WgXcQ"),
        id="yt fragment stripped",
    ),
    pytest.param(
        "https://user:pw@www.youtube.com:443/watch?v=dQw4w9WgXcQ",
        _yt("dQw4w9WgXcQ"),
        id="yt credentials + port stripped",
    ),
    pytest.param(
        "https://WWW.YouTube.com/watch?v=dQw4w9WgXcQ",
        _yt("dQw4w9WgXcQ"),
        id="yt uppercase host",
    ),
    pytest.param(
        "http://youtube.com/watch?v=dQw4w9WgXcQ",
        _yt("dQw4w9WgXcQ"),
        id="yt plain http",
    ),
    # --- youtube: errors ---
    pytest.param(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQx",
        _YT_UNSUPPORTED,
        id="yt 12-char id fails tester",
    ),
    pytest.param(
        "https://www.youtube.com/watch?v=",
        _YT_UNSUPPORTED,
        id="yt empty v",
    ),
    pytest.param(
        "https://www.youtube.com/playlist?list=PLx",
        _YT_UNSUPPORTED,
        id="yt playlist only",
    ),
    pytest.param(
        "https://www.youtube.com/@somechannel",
        _YT_UNSUPPORTED,
        id="yt channel page",
    ),
    pytest.param(
        "https://www.youtube.com/shorts/",
        _YT_UNSUPPORTED,
        id="yt shorts without id",
    ),
    pytest.param(
        "https://www.youtube.com/",
        _YT_UNSUPPORTED,
        id="yt homepage",
    ),
    pytest.param(
        "https://youtu.be/",
        _INVALID,
        id="yt youtu.be without id stays youtu.be",
    ),
    pytest.param(
        "https://www.youtube.de/watch?v=dQw4w9WgXcQ",
        _INVALID,
        id="yt wrong tld",
    ),
    pytest.param(
        "https://gaming.youtube.com/watch?v=dQw4w9WgXcQ",
        _INVALID,
        id="yt subdomain not allowed",
    ),
    pytest.param(
        "https://notyoutube.com/watch?v=dQw4w9WgXcQ",
        _INVALID,
        id="yt lookalike domain",
    ),
    # --- twitter: real links ---
    pytest.param(
        "https://twitter.com/X/status/1697304622749086011",
        _tw("X", "1697304622749086011"),
        id="tw real status",
    ),
    pytest.param(
        "https://twitter.com/X/status/1697304622749086011/mediaViewer"
        "?currentTweet=1697304622749086011&currentTweetUser=X"
        "&currentTweet=1697304622749086011&currentTweetUser=X",
        _tw("X", "1697304622749086011"),
        id="tw real mediaViewer + query",
    ),
    pytest.param(
        "https://twitter.com/dustbin_nie/status/1624596567188717568?s=20",
        _tw("dustbin_nie", "1624596567188717568"),
        id="tw real s=20",
    ),
    pytest.param(
        "https://twitter.com/sky_mj26/status/1807756010712428565",
        _tw("sky_mj26", "1807756010712428565"),
        id="tw real status 2",
    ),
    pytest.param(
        "https://x.com/PopCrave/status/1682176754792955905",
        _tw("PopCrave", "1682176754792955905"),
        id="tw real x.com",
    ),
    pytest.param(
        "https://x.com/eggsaladscreams/status/1693089534886506756?s=46",
        _tw("eggsaladscreams", "1693089534886506756"),
        id="tw real x.com s=46",
    ),
    pytest.param(
        "https://vxtwitter.com/dustbin_nie/status/1624596567188717568?s=20",
        _tw("dustbin_nie", "1624596567188717568"),
        id="tw real vxtwitter",
    ),
    pytest.param(
        "https://twitter.com/hugekiwinuts/status/1618671150829309953"
        "?s=46&t=gItGzgwGQQJJaJrO6qc1Pg",
        _tw("hugekiwinuts", "1618671150829309953"),
        id="tw real s + t tracking",
    ),
    pytest.param(
        "https://twitter.com/i/bookmarks?post_id=1828099210220294314",
        Extracted("twitter", {"id": "1828099210220294314"}),
        id="tw real bookmarks",
    ),
    pytest.param(
        "https://twitter.com/test/status/9487653",
        _tw("test", "9487653"),
        id="tw real nonexistent (cobalt 400 is network)",
    ),
    # --- twitter: other forms ---
    pytest.param(
        "https://fixvx.com/jack/status/20",
        _tw("jack", "20"),
        id="tw fixvx",
    ),
    pytest.param(
        "https://mobile.twitter.com/jack/status/20",
        _tw("jack", "20"),
        id="tw mobile subdomain",
    ),
    pytest.param(
        "https://www.x.com/jack/status/20",
        _tw("jack", "20"),
        id="tw www.x.com aliased (deviation from cobalt)",
    ),
    pytest.param(
        "https://mobile.x.com/jack/status/20?s=20",
        _tw("jack", "20"),
        id="tw mobile.x.com aliased (deviation from cobalt)",
    ),
    pytest.param(
        "https://twitter.com/i/status/1697304622749086011",
        _tw("i", "1697304622749086011"),
        id="tw i/status share form",
    ),
    pytest.param(
        "https://x.com/jack/status/20/video/1",
        _tw("jack", "20", index="1"),
        id="tw video index",
    ),
    pytest.param(
        "https://x.com/jack/status/20/photo/2",
        _tw("jack", "20", index="2"),
        id="tw photo index",
    ),
    pytest.param(
        "https://x.com/i/bookmarks?post_id=20&utm_source=x",
        Extracted("twitter", {"id": "20"}),
        id="tw bookmarks extra param stripped",
    ),
    pytest.param(
        "https://X.com/jack/status/20/",
        _tw("jack", "20"),
        id="tw uppercase alt host + trailing slash",
    ),
    pytest.param(
        "https://twitter.com/jack/status/20#reply",
        _tw("jack", "20"),
        id="tw fragment stripped",
    ),
    # --- twitter: errors ---
    # Deviation from cobalt: non-digit ids are rejected here, because Python's
    # int() raises where JS Number() quietly gives NaN.
    pytest.param(
        "https://x.com/jack/status/abc",
        _TW_UNSUPPORTED,
        id="tw non-numeric id rejected",
    ),
    pytest.param(
        "https://twitter.com/jack/status/" + "1" * 20,
        _TW_UNSUPPORTED,
        id="tw 20-digit id fails tester",
    ),
    pytest.param(
        "https://twitter.com/jack",
        _TW_UNSUPPORTED,
        id="tw profile page",
    ),
    pytest.param(
        "https://twitter.com/jack/STATUS/20",
        _TW_UNSUPPORTED,
        id="tw patterns are case-sensitive",
    ),
    pytest.param(
        "https://twitter.com/jack/status/20/analytics",
        _TW_UNSUPPORTED,
        id="tw unknown suffix",
    ),
    pytest.param(
        "https://twitter.com/i/bookmarks",
        _TW_UNSUPPORTED,
        id="tw bookmarks without post_id",
    ),
    pytest.param(
        "https://api.x.com/jack/status/20",
        _INVALID,
        id="tw api.x.com not aliased, not a service",
    ),
    pytest.param(
        "https://api.twitter.com/jack/status/20",
        _INVALID,
        id="tw subdomain not allowed",
    ),
    pytest.param(
        "https://twitter.co.uk/jack/status/20",
        _INVALID,
        id="tw wrong tld",
    ),
    # --- not a link at all ---
    pytest.param("", _INVALID, id="empty string"),
    pytest.param("not a url", _INVALID, id="plain text"),
    pytest.param(
        "https://example.com/watch?v=dQw4w9WgXcQ", _INVALID, id="unknown host"
    ),
]


def _run(url: str) -> Extracted | ExtractError:
    return extract(clean_url(alias_url(url)))


@pytest.mark.parametrize(("url", "expected"), PIPELINE_CASES)
def test_pipeline(url: str, expected: Extracted | ExtractError) -> None:
    assert _run(url) == expected
