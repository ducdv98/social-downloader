import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

import tldextract

from social_downloader.domain.errors import ErrorCode, ExtractError

_EXTRACTOR = tldextract.TLDExtract(suffix_list_urls=())

TWITTER_ALT_HOSTS = frozenset({"x.com", "vxtwitter.com", "fixvx.com"})
YOUTUBE_WATCH_PREFIXES = frozenset({"shorts", "live"})

QUERY_WHITELIST: dict[str, str] = {
    "twitter": "post_id",
    "youtube": "v",
}

_ALWAYS_ALLOWED_SUBDOMAINS: frozenset[str] = frozenset({"www", ""})

_PARAM_NAME = r":([a-zA-Z0-9]+)"
_CHARSET = r"a-zA-Z0-9_~ %@.:-"


def compile_pattern(pattern: str) -> re.Pattern[str]:
    """Compile a cobalt-style pattern (":user/status/:id") to a regex."""

    chunks = re.split(_PARAM_NAME, pattern)
    pieces: list[str] = []

    for i, chunk in enumerate(chunks):
        if i % 2 == 0:
            # Even index: literal text
            pieces.append(re.escape(chunk))
        else:
            # Odd index: parameter name
            pieces.append(f"(?P<{chunk}>[{_CHARSET}]+)")

    return re.compile("".join(pieces))


def _patterns(*patterns: str) -> tuple[re.Pattern[str], ...]:
    return tuple(compile_pattern(p) for p in patterns)


@dataclass(frozen=True)
class ServiceConfig:
    patterns: tuple[re.Pattern[str], ...]
    tester: Callable[[dict[str, str]], bool]
    tld: str = "com"
    subdomains: frozenset[str] | Literal["*"] = frozenset()


SERVICES: dict[str, ServiceConfig] = {
    "twitter": ServiceConfig(
        patterns=_patterns(
            ":user/status/:id",
            ":user/status/:id/video/:index",
            ":user/status/:id/photo/:index",
            ":user/status/:id/mediaviewer",
            ":user/status/:id/mediaViewer",
            "i/bookmarks?post_id=:id",
        ),
        tester=lambda pattern: (
            "id" in pattern and len(pattern["id"]) < 20
        ),  # Twitter IDs are 19 digits or less
        subdomains=frozenset({"mobile"}),
    ),
    "youtube": ServiceConfig(
        patterns=_patterns("watch?v=:id", "embed/:id", "watch/:id", "v/:id"),
        tester=lambda pattern: (
            "id" in pattern and len(pattern["id"]) <= 11
        ),  # YouTube IDs are 11 characters
        subdomains=frozenset({"m", "music"}),
    ),
}


@dataclass(frozen=True)
class Extracted:
    service: str
    params: dict[str, str]


def _youtube_watch_url(video_id: str) -> str:
    return f"https://youtube.com/watch?v={quote(video_id, safe='')}"


def _service_key(hostname: str | None) -> str:
    if not hostname:
        return ""
    return _EXTRACTOR(hostname).domain


def alias_url(url: str) -> str:
    """Rewrite alternate or short URLs into one canonical form.

    Pure and total: unknown or malformed input is returned unchanged.
    Validation (``link.invalid``) is a later step.
    """
    parts = urlsplit(url)
    host = parts.hostname
    # "/a/b" -> ["", "a", "b"]
    segments = parts.path.split("/")

    if host in TWITTER_ALT_HOSTS:
        return urlunsplit(parts._replace(netloc="twitter.com"))

    if host == "youtu.be" and len(segments) >= 2 and segments[1]:
        return _youtube_watch_url(segments[1])

    service_key = _service_key(host)

    if (
        service_key == "youtube"
        and len(segments) >= 3
        and segments[1] in YOUTUBE_WATCH_PREFIXES
        and segments[2]
    ):
        return _youtube_watch_url(segments[2])

    return url


def clean_url(url: str) -> str:
    parts = urlsplit(url)
    service_key = _service_key(parts.hostname)

    clean_netloc = parts.hostname or ""

    query: str = ""
    path = parts.path.removesuffix("/")

    if service_key in QUERY_WHITELIST:
        param = QUERY_WHITELIST[service_key]
        matching = [(k, v) for k, v in parse_qsl(parts.query) if k == param]
        # Several matches (?v=a&v=b): keep only the first, like cobalt.
        query = urlencode(matching[:1])

    return urlunsplit(
        parts._replace(netloc=clean_netloc, path=path, query=query, fragment="")
    )


def get_host_if_valid(url: str) -> str | None:
    """Return the service key of a URL if it is a known service and valid, else None."""

    hostname = urlsplit(url).hostname
    if not hostname:
        return None

    extracted_url = _EXTRACTOR(hostname)
    domain = extracted_url.domain

    if not domain:
        return None

    service = SERVICES.get(domain)

    if service is None:
        return None

    if service.tld != extracted_url.suffix:
        return None

    if extracted_url.subdomain in _ALWAYS_ALLOWED_SUBDOMAINS:
        return extracted_url.domain

    if service.subdomains != "*" and extracted_url.subdomain not in service.subdomains:
        return None

    return extracted_url.domain


def extract(
    url: str, enabled_services: frozenset[str] = frozenset(SERVICES)
) -> Extracted | ExtractError:
    """Match a normalized URL to a service and its pattern params.

    Returns ExtractError with LINK_INVALID, SERVICE_DISABLED or LINK_UNSUPPORTED.
    """

    service_key = get_host_if_valid(url)
    if service_key is None:
        return ExtractError(ErrorCode.LINK_INVALID)

    if service_key not in enabled_services:
        return ExtractError(ErrorCode.SERVICE_DISABLED)

    parts = urlsplit(url)
    service = SERVICES[service_key]
    query = parts.query
    path = parts.path[1:]  # Remove leading slash

    target = path
    if query:
        target += "?" + query

    for pattern in service.patterns:
        match = pattern.fullmatch(target)
        if match is not None:
            params = match.groupdict()
            if not service.tester(params):
                return ExtractError(
                    ErrorCode.LINK_UNSUPPORTED, {"service": service_key}
                )
            return Extracted(service_key, params)

    return ExtractError(ErrorCode.LINK_UNSUPPORTED, {"service": service_key})
