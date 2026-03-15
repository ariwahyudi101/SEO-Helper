from __future__ import annotations

from dataclasses import dataclass

from seo_audit.geo_analyzer import GEOScores
from seo_audit.parser import PageSignals


@dataclass
class ScoreCard:
    technical_seo: int
    content_quality: int
    geo: int
    overall: int


def compute_scores(signals: list[PageSignals], geo_scores: GEOScores) -> ScoreCard:
    if not signals:
        return ScoreCard(0, 0, geo_scores.overall_geo, 0)

    technical_penalties = 0
    content_penalties = 0
    for s in signals:
        technical_penalties += 8 if not s.indexable else 0
        technical_penalties += 5 if s.canonical_conflict else 0
        technical_penalties += 3 if s.missing_alt_count else 0
        content_penalties += 8 if s.thin_content else 0
        content_penalties += 5 if not s.meta_description else 0
        content_penalties += 5 if not s.title else 0

    technical = max(0, 100 - int(technical_penalties / len(signals)))
    content = max(0, 100 - int(content_penalties / len(signals)))
    overall = int(technical * 0.4 + content * 0.35 + geo_scores.overall_geo * 0.25)
    return ScoreCard(technical, content, geo_scores.overall_geo, overall)


def generate_markdown_report(
    start_url: str,
    crawl_summary: dict,
    signals: list[PageSignals],
    geo_scores: GEOScores,
    ai_simulations: list[dict],
) -> tuple[str, ScoreCard]:
    scores = compute_scores(signals, geo_scores)

    issues = []
    for page in signals:
        for issue in page.issues:
            issues.append((page.url, issue))

    top_issues = issues[:10]
    page_findings = "\n".join(f"- **{s.url}**: {', '.join(s.issues) if s.issues else 'No major issues'}" for s in signals[:25])
    action_plan = "\n".join(
        [
            "1. Fix indexability and canonical conflicts on high-value pages.",
            "2. Improve thin pages with expert-depth sections and supporting entities.",
            "3. Add/validate JSON-LD schema and complete image alt coverage.",
            "4. Strengthen internal links to core revenue or conversion pages.",
            "5. Publish FAQ/How-to chunks to improve AI citation probability.",
        ]
    )

    md = f"""
# SEO Audit Report: {start_url}

## Executive Summary
- Technical SEO: **{scores.technical_seo}/100**
- Content Quality: **{scores.content_quality}/100**
- AI SEO / GEO: **{scores.geo}/100**
- Weighted Overall: **{scores.overall}/100**

## Crawl Overview
- Discovered URLs: {crawl_summary['discovered']}
- Crawled URLs: {crawl_summary['crawled']}
- Blocked by robots: {crawl_summary['blocked']}
- Failed URLs: {crawl_summary['failed']}

## Technical SEO
- Canonical conflicts: {sum(1 for s in signals if s.canonical_conflict)}
- Non-indexable pages: {sum(1 for s in signals if not s.indexable)}
- Missing alt text pages: {sum(1 for s in signals if s.missing_alt_count > 0)}

## On-Page SEO
- Missing title tags: {sum(1 for s in signals if not s.title)}
- Missing meta descriptions: {sum(1 for s in signals if not s.meta_description)}
- H1 hierarchy issues: {sum(1 for s in signals if s.heading_hierarchy_issues)}

## Content Quality
- Thin content pages: {sum(1 for s in signals if s.thin_content)}
- Avg word count: {int(sum((s.word_count for s in signals), 0) / max(1, len(signals)))}

## Internal Linking
- Avg internal links: {int(sum((s.internal_links for s in signals), 0) / max(1, len(signals)))}
- Avg external links: {int(sum((s.external_links for s in signals), 0) / max(1, len(signals)))}

## Metadata/Structured Data
- Pages with schema types: {sum(1 for s in signals if s.schema_types)}
- Most common schema examples: {', '.join(sorted({t for s in signals for t in s.schema_types})[:5]) or 'None'}

## Indexability/Crawlability
- Robots-blocked URLs: {crawl_summary['blocked']}
- Crawl failures: {crawl_summary['failed']}

## AI Search Optimization (GEO)
- Answer readiness: {geo_scores.answer_readiness}
- Chunkability: {geo_scores.chunkability}
- Entity coverage: {geo_scores.entity_coverage}
- Topical authority: {geo_scores.topical_authority}
- Brand/author signals: {geo_scores.brand_author_signals}
- Citation likelihood: {geo_scores.citation_likelihood}

## AI Answer Simulation
{chr(10).join([f"- Q: {r['question']} (citation probability: {r['citation_probability']}, likely page: {r['likely_page']})" for r in ai_simulations])}

## Top Problems
{chr(10).join([f"- {u}: {i}" for u, i in top_issues]) or '- No critical issues detected.'}

## Priority Action Plan
{action_plan}

## Page-Level Findings
{page_findings}

## Recommendations
- Implement metadata templates to prevent title/description omissions.
- Add context-rich schema and explicit author trust signals.
- Improve topical clusters and internal linking from hub pages.
- Track future audits to validate score improvements over time.
""".strip()

    return md, scores
