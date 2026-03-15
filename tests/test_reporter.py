from seo_audit.geo_analyzer import GEOScores
from seo_audit.parser import PageSignals
from seo_audit.reporter import compute_scores


def _page(url: str, thin: bool = False, indexable: bool = True) -> PageSignals:
    return PageSignals(
        url=url,
        title="Title",
        meta_description="Desc",
        canonical=url,
        robots_meta=None,
        og_tags={},
        twitter_tags={},
        h1=["H1"],
        h2=[],
        heading_hierarchy_issues=[],
        word_count=600 if not thin else 100,
        paragraph_count=5,
        thin_content=thin,
        internal_links=3,
        external_links=1,
        broken_link_refs=[],
        image_count=2,
        missing_alt_count=0,
        schema_types=["Article"],
        indexable=indexable,
        canonical_conflict=False,
        issues=[],
    )


def test_compute_scores_range():
    geo = GEOScores(60, 60, 60, 60, 60, 60, 60)
    scores = compute_scores([_page("https://example.com")], geo)
    assert 0 <= scores.technical_seo <= 100
    assert 0 <= scores.content_quality <= 100
    assert 0 <= scores.overall <= 100
