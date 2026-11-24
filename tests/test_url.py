import pytest

from social_downloader.domain.url import alias_url, clean_url, get_host_if_valid

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
    pytest.param("", "", id="empty string"),
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
