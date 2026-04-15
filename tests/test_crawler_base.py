import pytest
from crawlers.base import BaseCrawler, CrawlResult

def test_crawl_result_structure():
    result = CrawlResult(
        site="금천미트",
        grade="2등급",
        cut="목심",
        gender="암소",
        price_per_kg=18500,
        weight_kg=10.2,
        url="https://example.com/1",
    )
    assert result.site == "금천미트"
    assert result.price_per_kg == 18500

def test_base_crawler_requires_fetch_implementation():
    class IncompleteCrawler(BaseCrawler):
        pass

    with pytest.raises(TypeError):
        IncompleteCrawler()

def test_base_crawler_to_dict():
    class DummyCrawler(BaseCrawler):
        def fetch(self):
            return [
                CrawlResult(
                    site="테스트",
                    grade="2등급",
                    cut="목심",
                    gender="거세",
                    price_per_kg=17000,
                    weight_kg=20.0,
                    url="https://test.com",
                )
            ]

    crawler = DummyCrawler()
    results = crawler.fetch()
    data = crawler.to_dict(results)
    assert isinstance(data, list)
    assert data[0]["site"] == "테스트"
    assert "crawled_at" in data[0]
