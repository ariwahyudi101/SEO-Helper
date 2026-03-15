from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup


@dataclass
class PageSignals:
    url: str
    title: str | None
    meta_description: str | None
    canonical: str | None
    robots_meta: str | None
    og_tags: dict[str, str]
    twitter_tags: dict[str, str]
    h1: list[str]
    h2: list[str]
    heading_hierarchy_issues: list[str]
    word_count: int
    paragraph_count: int
    thin_content: bool
    internal_links: int
    external_links: int
    broken_link_refs: list[str]
    image_count: int
    missing_alt_count: int
    schema_types: list[str]
    indexable: bool
    canonical_conflict: bool
    issues: list[str] = field(default_factory=list)


def _safe_text(tag: Any) -> str | None:
    if not tag:
        return None
    text = tag.get_text(strip=True)
    return text if text else None


def parse_page(url: str, html: str, status_code: int | None = None) -> PageSignals:
    soup = BeautifulSoup(html, "lxml")
    title = _safe_text(soup.title)
    meta_desc_tag = soup.find("meta", attrs={"name": "description"})
    meta_description = meta_desc_tag.get("content", "").strip() if meta_desc_tag else None

    canonical_tag = soup.find("link", attrs={"rel": "canonical"})
    canonical = canonical_tag.get("href", "").strip() if canonical_tag else None

    robots_tag = soup.find("meta", attrs={"name": "robots"})
    robots_meta = robots_tag.get("content", "").strip().lower() if robots_tag else None

    og_tags = {
        tag.get("property"): tag.get("content", "")
        for tag in soup.find_all("meta", attrs={"property": True})
        if str(tag.get("property", "")).startswith("og:")
    }
    twitter_tags = {
        tag.get("name"): tag.get("content", "")
        for tag in soup.find_all("meta", attrs={"name": True})
        if str(tag.get("name", "")).startswith("twitter:")
    }

    h1 = [_safe_text(tag) or "" for tag in soup.find_all("h1")]
    h2 = [_safe_text(tag) or "" for tag in soup.find_all("h2")]
    hierarchy_issues: list[str] = []
    if len(h1) == 0:
        hierarchy_issues.append("Missing H1")
    if len(h1) > 1:
        hierarchy_issues.append("Multiple H1 tags")
    if h2 and not h1:
        hierarchy_issues.append("H2 present without H1")

    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    words = [w for p in paragraphs for w in p.split()]
    word_count = len(words)
    thin_content = word_count < 300

    internal = 0
    external = 0
    broken_link_refs: list[str] = []
    current_host = urlparse(url).hostname or ""
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href.startswith("#") or href.startswith("javascript:"):
            continue
        if href.startswith(("http://", "https://")):
            if (urlparse(href).hostname or "") == current_host:
                internal += 1
            else:
                external += 1
        else:
            internal += 1
        if "404" in link.get_text("", strip=True).lower():
            broken_link_refs.append(href)

    images = soup.find_all("img")
    missing_alt = sum(1 for image in images if not image.get("alt"))

    schema_types: list[str] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            payload = json.loads(script.string or "{}")
            if isinstance(payload, dict) and "@type" in payload:
                schema_types.append(str(payload["@type"]))
            elif isinstance(payload, list):
                for item in payload:
                    if isinstance(item, dict) and "@type" in item:
                        schema_types.append(str(item["@type"]))
        except json.JSONDecodeError:
            continue

    indexable = not robots_meta or ("noindex" not in robots_meta and (status_code or 200) < 400)
    canonical_conflict = bool(canonical and canonical != url)

    issues: list[str] = []
    if not title:
        issues.append("Missing title")
    if not meta_description:
        issues.append("Missing meta description")
    if thin_content:
        issues.append("Thin content")
    if missing_alt > 0:
        issues.append("Images missing alt text")
    issues.extend(hierarchy_issues)
    if not indexable:
        issues.append("Page not indexable")
    if canonical_conflict:
        issues.append("Canonical points to different URL")

    return PageSignals(
        url=url,
        title=title,
        meta_description=meta_description,
        canonical=canonical,
        robots_meta=robots_meta,
        og_tags=og_tags,
        twitter_tags=twitter_tags,
        h1=h1,
        h2=h2,
        heading_hierarchy_issues=hierarchy_issues,
        word_count=word_count,
        paragraph_count=len(paragraphs),
        thin_content=thin_content,
        internal_links=internal,
        external_links=external,
        broken_link_refs=broken_link_refs,
        image_count=len(images),
        missing_alt_count=missing_alt,
        schema_types=schema_types,
        indexable=indexable,
        canonical_conflict=canonical_conflict,
        issues=issues,
    )
