from urllib import robotparser


def test_robots_filtering():
    rp = robotparser.RobotFileParser()
    rp.parse(["User-agent: *", "Disallow: /private"])
    assert rp.can_fetch("*", "https://example.com/public")
    assert not rp.can_fetch("*", "https://example.com/private/page")
