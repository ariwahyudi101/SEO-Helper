from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Iterable
from urllib import robotparser
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from seo_audit.utils import is_same_host, normalize_url


@dataclass
class CrawlPage:
    url: str
    final_url: str | None = None
    status_code: int | None = None
    html: str | None = None
    redirect_chain: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class CrawlResult:
    start_url: str
    discovered_urls: set[str] = field(default_factory=set)
    crawled_pages: list[CrawlPage] = field(default_factory=list)
    blocked_urls: set[str] = field(default_factory=set)
    failed_urls: dict[str, str] = field(default_factory=dict)


def fetch_robots_parser(session: requests.Session, root_url: str, timeout: float) -> robotparser.RobotFileParser:
    parsed = urlparse(root_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = robotparser.RobotFileParser()
    rp.set_url(robots_url)
    try:
        response = session.get(robots_url, timeout=timeout)
        if response.ok:
            rp.parse(response.text.splitlines())
        else:
            rp.parse([])
    except requests.RequestException:
        rp.parse([])
    return rp


def parse_sitemap_xml(xml_text: str) -> list[str]:
    soup = BeautifulSoup(xml_text, "xml")
    loc_tags = soup.find_all("loc")
    return [tag.text.strip() for tag in loc_tags if tag.text]


def discover_sitemaps(session: requests.Session, root_url: str, timeout: float) -> list[str]:
    parsed = urlparse(root_url)
    candidate_urls = [f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"]
    found: list[str] = []

    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        robots_resp = session.get(robots_url, timeout=timeout)
        for line in robots_resp.text.splitlines():
            if line.lower().startswith("sitemap:"):
                candidate_urls.append(line.split(":", 1)[1].strip())
    except requests.RequestException:
        pass

    for sm_url in dict.fromkeys(candidate_urls):
        try:
            resp = session.get(sm_url, timeout=timeout)
            if not resp.ok:
                continue
            found.extend(parse_sitemap_xml(resp.text))
        except requests.RequestException:
            continue
    return found


def extract_links(html: str, base_url: str) -> Iterable[str]:
    soup = BeautifulSoup(html, "lxml")
    for anchor in soup.find_all("a", href=True):
        yield normalize_url(anchor["href"], base_url)


def crawl_site(start_url: str, max_pages: int = 50, rate_limit: float = 0.0, timeout: float = 15.0) -> CrawlResult:
    import time

    session = requests.Session()
    start_url = normalize_url(start_url)
    root_host = urlparse(start_url).hostname or ""

    result = CrawlResult(start_url=start_url)
    rp = fetch_robots_parser(session, start_url, timeout)

    queue = deque([start_url])
    sitemap_urls = [normalize_url(url, start_url) for url in discover_sitemaps(session, start_url, timeout)]
    queue.extend(url for url in sitemap_urls if is_same_host(url, root_host))

    seen: set[str] = set()

    while queue and len(result.crawled_pages) < max_pages:
        current = normalize_url(queue.popleft(), start_url)
        if current in seen:
            continue
        seen.add(current)
        result.discovered_urls.add(current)

        if not is_same_host(current, root_host):
            continue
        if not rp.can_fetch("*", current):
            result.blocked_urls.add(current)
            continue

        try:
            response = session.get(current, timeout=timeout, allow_redirects=True)
            chain = [resp.url for resp in response.history] + [response.url]
            page = CrawlPage(
                url=current,
                final_url=normalize_url(response.url),
                status_code=response.status_code,
                html=response.text if "text/html" in response.headers.get("Content-Type", "") else None,
                redirect_chain=chain,
            )
            result.crawled_pages.append(page)

            if page.html:
                for link in extract_links(page.html, page.final_url or current):
                    norm = normalize_url(link)
                    if norm not in seen and is_same_host(norm, root_host):
                        queue.append(norm)
                        result.discovered_urls.add(norm)
        except requests.RequestException as exc:
            result.failed_urls[current] = str(exc)
            result.crawled_pages.append(CrawlPage(url=current, error=str(exc)))

        if rate_limit > 0:
            time.sleep(rate_limit)

    while queue:
        left = normalize_url(queue.popleft(), start_url)
        if left not in seen:
            result.discovered_urls.add(left)

    return result
