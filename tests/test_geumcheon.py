import pytest
from unittest.mock import MagicMock, patch
from crawlers.geumcheon import GeumcheonCrawler
from crawlers.base import CrawlResult

def make_mock_product(grade_text, price_text, weight_text, href):
    product = MagicMock()
    product.get_attribute.return_value = href
    grade_el = MagicMock()
    grade_el.inner_text.return_value = grade_text
    price_el = MagicMock()
    price_el.inner_text.return_value = price_text
    weight_el = MagicMock()
    weight_el.inner_text.return_value = weight_text
    def query_selector(sel):
        if ".chip.type1" in sel:
            return grade_el
        if ".pd-price.c-primary" in sel:
            return price_el
        if ".chip-weight" in sel:
            return weight_el
        return None
    product.query_selector.side_effect = query_selector
    return product

def test_parse_returns_2grade_only():
    crawler = GeumcheonCrawler()
    mock_page = MagicMock()
    mock_page.query_selector_all.return_value = [
        make_mock_product("2A", "24,600원", "5.9kg", "/pd/productDetail?goodsNo=123"),
        make_mock_product("1++B", "28,000원", "12.0kg", "/pd/productDetail?goodsNo=456"),
        make_mock_product("2C", "25,200원", "7.2kg", "/pd/productDetail?goodsNo=789"),
    ]
    results = crawler._parse(mock_page, "암소")
    assert len(results) == 2
    assert all(r.grade == "2등급" for r in results)
    assert all(r.cut == "목심" for r in results)
    assert all(r.gender == "암소" for r in results)

def test_parse_price_and_weight_extracted():
    crawler = GeumcheonCrawler()
    mock_page = MagicMock()
    mock_page.query_selector_all.return_value = [
        make_mock_product("2A", "24,600원", "5.9kg", "/pd/productDetail?goodsNo=123"),
    ]
    results = crawler._parse(mock_page, "거세")
    assert results[0].price_per_kg == 24600
    assert results[0].weight_kg == 5.9
    assert "goodsNo=123" in results[0].url

def test_parse_skips_zero_price():
    crawler = GeumcheonCrawler()
    mock_page = MagicMock()
    mock_page.query_selector_all.return_value = [
        make_mock_product("2B", "", "5.0kg", "/pd/productDetail?goodsNo=999"),
    ]
    results = crawler._parse(mock_page, "암소")
    assert len(results) == 0

def test_fetch_returns_empty_on_playwright_error():
    crawler = GeumcheonCrawler()
    with patch("crawlers.geumcheon.sync_playwright") as mock_pw:
        mock_pw.side_effect = Exception("playwright 오류")
        results = crawler.fetch()
    assert results == []
