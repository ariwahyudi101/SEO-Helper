from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
}


def normalize_url(url: str, base_url: str | None = None) -> str:
    candidate = urljoin(base_url, url) if base_url else url
    parsed = urlparse(candidate)
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]

    filtered = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k not in TRACKING_PARAMS]
    query = urlencode(sorted(filtered))

    return urlunparse((scheme, netloc, path, "", query, ""))


def extract_root_domain(url: str) -> str:
    host = urlparse(url).hostname or ""
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    return ".".join(parts[-2:])


def is_same_host(candidate: str, root: str) -> bool:
    host = urlparse(candidate).hostname or ""
    return host == root
