from dataclasses import dataclass
from typing import Literal
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

import tldextract

_EXTRACTOR = tldextract.TLDExtract(suffix_list_urls=())

TWITTER_ALT_HOSTS = frozenset({"x.com", "vxtwitter.com", "fixvx.com"})
YOUTUBE_HOSTS = frozenset({"youtube.com", "www.youtube.com", "m.youtube.com"})
YOUTUBE_WATCH_PREFIXES = frozenset({"shorts", "live"})

QUERY_WHITELIST: dict[str, str] = {
    "twitter.com": "post_id",
    **dict.fromkeys(YOUTUBE_HOSTS, "v"),
}

_ALWAYS_ALLOWED_SUBDOMAINS: frozenset[str] = frozenset({"www", ""})


@dataclass(frozen=True)
class ServiceConfig:
    tld: str = "com"
    subdomains: frozenset[str] | Literal["*"] = frozenset()


SERVICES: dict[str, ServiceConfig] = {
    "twitter": ServiceConfig(tld="com", subdomains=frozenset({"mobile"})),
    "youtube": ServiceConfig(tld="com", subdomains=frozenset({"m", "music"})),
}


def _youtube_watch_url(video_id: str) -> str:
    return f"https://youtube.com/watch?v={quote(video_id, safe='')}"


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

    if (
        host in YOUTUBE_HOSTS
        and len(segments) >= 3
        and segments[1] in YOUTUBE_WATCH_PREFIXES
        and segments[2]
    ):
        return _youtube_watch_url(segments[2])

    return url


def clean_url(url: str) -> str:
    parts = urlsplit(url)

    clean_netloc = parts.hostname or ""

    query: str = ""
    path = parts.path.removesuffix("/")

    if parts.hostname in QUERY_WHITELIST:
        param = QUERY_WHITELIST[parts.hostname]
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
