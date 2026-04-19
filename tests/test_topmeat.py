import pytest
from unittest.mock import patch, MagicMock
from crawlers.topmeat import TopMeatCrawler
from crawlers.base import CrawlResult

# 실제 사이트 HTML hidden input 구조 기반 샘플
SAMPLE_HTML = """
<input type="hidden" name="it_id[0]" value="892604159999214060103000068">
<input type="hidden" name="it_name[0]" value="한우거세 목심">
<input type="hidden" name="it_amount[0]" value="250290">
<input type="hidden" name="it_maker2[0]" value="24300">
<input type="hidden" name="it_origin1[0]" value="10.3">
<input type="hidden" name="it_maker5[0]" value="2">

<input type="hidden" name="it_id[1]" value="892604159999214060101000084">
<input type="hidden" name="it_name[1]" value="한우거세 목심">
<input type="hidden" name="it_amount[1]" value="245430">
<input type="hidden" name="it_maker2[1]" value="24300">
<input type="hidden" name="it_origin1[1]" value="10.1">
<input type="hidden" name="it_maker5[1]" value="2">

<input type="hidden" name="it_id[2]" value="892604169999214060111000070">
<input type="hidden" name="it_name[2]" value="한우거세 목심">
<input type="hidden" name="it_amount[2]" value="271950">
<input type="hidden" name="it_maker2[2]" value="24500">
<input type="hidden" name="it_origin1[2]" value="11.1">
<input type="hidden" name="it_maker5[2]" value="2">
"""

EMPTY_HTML = "<html><body></body></html>"


def test_parse_returns_results():
    crawler = TopMeatCrawler()
    results = crawler._parse(SAMPLE_HTML, "거세")
    assert len(results) == 3
    assert all(isinstance(r, CrawlResult) for r in results)


def test_price_per_kg_parsed():
    crawler = TopMeatCrawler()
    results = crawler._parse(SAMPLE_HTML, "거세")
    assert results[0].price_per_kg == 24300
    assert results[2].price_per_kg == 24500


def test_weight_kg_parsed():
    crawler = TopMeatCrawler()
    results = crawler._parse(SAMPLE_HTML, "거세")
    assert results[0].weight_kg == 10.3
    assert results[1].weight_kg == 10.1
    assert results[2].weight_kg == 11.1


def test_grade_format():
    crawler = TopMeatCrawler()
    results = crawler._parse(SAMPLE_HTML, "거세")
    assert results[0].grade == "2등급"


def test_gender_assigned():
    crawler = TopMeatCrawler()
    results_geose = crawler._parse(SAMPLE_HTML, "거세")
    results_amso = crawler._parse(SAMPLE_HTML, "암소")
    assert all(r.gender == "거세" for r in results_geose)
    assert all(r.gender == "암소" for r in results_amso)


def test_cut_is_moksim():
    crawler = TopMeatCrawler()
    results = crawler._parse(SAMPLE_HTML, "거세")
    assert all(r.cut == "목심" for r in results)


def test_url_contains_it_id():
    crawler = TopMeatCrawler()
    results = crawler._parse(SAMPLE_HTML, "거세")
    assert "892604159999214060103000068" in results[0].url
    assert "topmeat.co.kr" in results[0].url


def test_empty_html_returns_empty():
    crawler = TopMeatCrawler()
    results = crawler._parse(EMPTY_HTML, "거세")
    assert results == []


def test_fetch_returns_empty_on_playwright_error():
    crawler = TopMeatCrawler()
    with patch("crawlers.topmeat.sync_playwright") as mock_pw:
        mock_pw.side_effect = Exception("Playwright 오류")
        results = crawler.fetch()
    assert results == []
