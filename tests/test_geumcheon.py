import pytest
from unittest.mock import patch, MagicMock
from crawlers.geumcheon import GeumcheonCrawler
from crawlers.base import CrawlResult

SAMPLE_ITEM = {
    "goodsNo": 26150290,
    "lsprdGrdCd": "2",
    "korthsMwgtGrdCd": "A",
    "lventSexGbNm": "암",
    "invtWgt": 5.9,
    "salePrc": 145140,
    "totCnt": 2,
}

SAMPLE_ITEM_2 = {
    "goodsNo": 26150291,
    "lsprdGrdCd": "2",
    "korthsMwgtGrdCd": "B",
    "lventSexGbNm": "암",
    "invtWgt": 8.0,
    "salePrc": 200000,
    "totCnt": 2,
}

def mock_post_response(items):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"payload": items}
    mock_resp.raise_for_status = MagicMock()
    return mock_resp

def test_fetch_returns_crawl_results():
    crawler = GeumcheonCrawler()
    with patch("crawlers.geumcheon.requests.post") as mock_post:
        mock_post.return_value = mock_post_response([SAMPLE_ITEM, SAMPLE_ITEM_2])
        results = crawler.fetch()
    assert len(results) > 0
    assert all(isinstance(r, CrawlResult) for r in results)

def test_price_per_kg_calculated_correctly():
    crawler = GeumcheonCrawler()
    with patch("crawlers.geumcheon.requests.post") as mock_post:
        mock_post.return_value = mock_post_response([SAMPLE_ITEM])
        results = crawler.fetch()
    암소_results = [r for r in results if r.gender == "암소"]
    assert len(암소_results) > 0
    # 145140 / 5.9 = 24,600 (rounded)
    assert 암소_results[0].price_per_kg == round(145140 / 5.9)

def test_grade_includes_quality():
    crawler = GeumcheonCrawler()
    with patch("crawlers.geumcheon.requests.post") as mock_post:
        mock_post.return_value = mock_post_response([SAMPLE_ITEM])
        results = crawler.fetch()
    암소_results = [r for r in results if r.gender == "암소"]
    assert 암소_results[0].grade == "2등급A"

def test_fetch_returns_empty_on_api_error():
    crawler = GeumcheonCrawler()
    with patch("crawlers.geumcheon.requests.post") as mock_post:
        mock_post.side_effect = Exception("API 오류")
        results = crawler.fetch()
    assert results == []

def test_skips_zero_weight_items():
    crawler = GeumcheonCrawler()
    bad_item = {**SAMPLE_ITEM, "invtWgt": 0, "totCnt": 1}
    with patch("crawlers.geumcheon.requests.post") as mock_post:
        mock_post.return_value = mock_post_response([bad_item])
        results = crawler.fetch()
    assert all(r.weight_kg > 0 for r in results)
