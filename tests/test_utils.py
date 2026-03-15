from seo_audit.utils import extract_root_domain, normalize_url


def test_normalize_url_strips_tracking_and_fragment():
    url = "HTTPS://Example.com/path/?utm_source=x&a=1#frag"
    assert normalize_url(url) == "https://example.com/path?a=1"


def test_extract_root_domain():
    assert extract_root_domain("https://blog.example.com/page") == "example.com"
