from seo_audit.crawler import parse_sitemap_xml


def test_parse_sitemap_xml():
    xml = """
    <urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>
      <url><loc>https://example.com/</loc></url>
      <url><loc>https://example.com/about</loc></url>
    </urlset>
    """
    urls = parse_sitemap_xml(xml)
    assert "https://example.com/" in urls
    assert "https://example.com/about" in urls
