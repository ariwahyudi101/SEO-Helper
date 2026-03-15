from __future__ import annotations

from dataclasses import dataclass

from seo_audit.parser import PageSignals


@dataclass
class GEOScores:
    answer_readiness: int
    chunkability: int
    entity_coverage: int
    topical_authority: int
    brand_author_signals: int
    citation_likelihood: int
    overall_geo: int


def compute_geo_scores(signals: list[PageSignals]) -> GEOScores:
    if not signals:
        return GEOScores(0, 0, 0, 0, 0, 0, 0)

    avg_words = sum(s.word_count for s in signals) / len(signals)
    schema_ratio = sum(1 for s in signals if s.schema_types) / len(signals)
    title_ratio = sum(1 for s in signals if s.title) / len(signals)
    brand_ratio = sum(1 for s in signals if s.og_tags or s.twitter_tags) / len(signals)

    answer_readiness = min(100, int((avg_words / 1200) * 100))
    chunkability = min(100, int((sum(len(s.h2) for s in signals) / max(1, len(signals) * 5)) * 100))
    entity_coverage = min(100, int(schema_ratio * 100))
    topical_authority = min(100, int((title_ratio * 0.5 + (avg_words / 1500) * 0.5) * 100))
    brand_author_signals = min(100, int(brand_ratio * 100))
    citation_likelihood = min(100, int((schema_ratio * 0.5 + brand_ratio * 0.3 + title_ratio * 0.2) * 100))

    overall = int(
        answer_readiness * 0.2
        + chunkability * 0.15
        + entity_coverage * 0.2
        + topical_authority * 0.2
        + brand_author_signals * 0.1
        + citation_likelihood * 0.15
    )
    return GEOScores(
        answer_readiness,
        chunkability,
        entity_coverage,
        topical_authority,
        brand_author_signals,
        citation_likelihood,
        overall,
    )


def simulate_ai_answers(signals: list[PageSignals]) -> list[dict]:
    top_pages = sorted(signals, key=lambda x: x.word_count, reverse=True)[:5]
    simulations = []
    for idx, page in enumerate(top_pages, start=1):
        question = f"What should a user know about topic #{idx} from {page.url}?"
        citation_probability = min(0.95, max(0.1, page.word_count / 2500))
        snippet = (page.meta_description or page.title or "No snippet")[:180]
        content_gap = "Add explicit FAQ with concise answers" if page.word_count < 800 else "Expand entity references"
        simulations.append(
            {
                "question": question,
                "citation_probability": round(citation_probability, 2),
                "likely_page": page.url,
                "snippet": snippet,
                "content_gap": content_gap,
            }
        )
    return simulations
