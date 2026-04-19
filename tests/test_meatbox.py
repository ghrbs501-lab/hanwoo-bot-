import pytest
from unittest.mock import patch, MagicMock
from crawlers.meatbox import MeatboxCrawler
from crawlers.base import CrawlResult

SAMPLE_PRODUCT = {
    "productSeq": 336499,
    "itemSeq": 0,
    "itemKindCd": "D000",
    "itemKindName": "한우암소",
    "itemCatCd": "264",
    "itemCatName": "목심",
    "itemCattleInfo": {
        "qgrade": "2",
        "wgrade": "B",
        "gradeNm": "2B",
        "weight": "393",
    },
    "priceText": "24,500원",
    "priceUnitTypeText": "(kg당)",
    "stockAmount": 2,
}

SAMPLE_ITEM_1 = {
    "productSeq": 336499,
    "itemSeq": 5522742,
    "finalPricePerKg": 24500,
    "avgKg": 17.1,
    "statusCd": "AO02",
    "restAmount": 1,
}

SAMPLE_ITEM_2 = {
    "productSeq": 336499,
    "itemSeq": 5522741,
    "finalPricePerKg": 24500,
    "avgKg": 20.2,
    "statusCd": "AO02",
    "restAmount": 1,
}


def mock_search_response(products):
    mock = MagicMock()
    mock.status_code = 200
    mock.raise_for_status = MagicMock()
    mock.json.return_value = {"message": "ok", "resultCode": "0000", "data": {"search": {"items": products}}}
    return mock


def mock_items_response(items):
    mock = MagicMock()
    mock.status_code = 200
    mock.raise_for_status = MagicMock()
    mock.json.return_value = {"message": "ok", "resultCode": "0000", "data": {"sortedPricePerKgItems": items}}
    return mock


def test_fetch_returns_crawl_results():
    crawler = MeatboxCrawler()
    with patch("crawlers.meatbox.requests.post") as mock_post, \
         patch("crawlers.meatbox.requests.get") as mock_get:
        mock_post.return_value = mock_search_response([SAMPLE_PRODUCT])
        mock_get.return_value = mock_items_response([SAMPLE_ITEM_1, SAMPLE_ITEM_2])

        results = crawler.fetch()

    assert len(results) == 2
    assert all(isinstance(r, CrawlResult) for r in results)


def test_weight_from_items_api():
    crawler = MeatboxCrawler()
    with patch("crawlers.meatbox.requests.post") as mock_post, \
         patch("crawlers.meatbox.requests.get") as mock_get:
        mock_post.return_value = mock_search_response([SAMPLE_PRODUCT])
        mock_get.return_value = mock_items_response([SAMPLE_ITEM_1])

        results = crawler.fetch()

    assert results[0].weight_kg == 17.1
    assert results[0].price_per_kg == 24500


def test_grade_format():
    crawler = MeatboxCrawler()
    with patch("crawlers.meatbox.requests.post") as mock_post, \
         patch("crawlers.meatbox.requests.get") as mock_get:
        mock_post.return_value = mock_search_response([SAMPLE_PRODUCT])
        mock_get.return_value = mock_items_response([SAMPLE_ITEM_1])

        results = crawler.fetch()

    assert results[0].grade == "2등급B"


def test_gender_mapping():
    crawler = MeatboxCrawler()
    geose_product = {**SAMPLE_PRODUCT, "itemKindName": "한우거세"}
    with patch("crawlers.meatbox.requests.post") as mock_post, \
         patch("crawlers.meatbox.requests.get") as mock_get:
        mock_post.return_value = mock_search_response([geose_product])
        mock_get.return_value = mock_items_response([SAMPLE_ITEM_1])

        results = crawler.fetch()

    assert results[0].gender == "거세"


def test_filters_non_grade2():
    crawler = MeatboxCrawler()
    grade3_product = {
        **SAMPLE_PRODUCT,
        "itemCattleInfo": {**SAMPLE_PRODUCT["itemCattleInfo"], "qgrade": "3"},
    }
    with patch("crawlers.meatbox.requests.post") as mock_post, \
         patch("crawlers.meatbox.requests.get") as mock_get:
        mock_post.return_value = mock_search_response([grade3_product])
        mock_get.return_value = mock_items_response([SAMPLE_ITEM_1])

        results = crawler.fetch()

    assert results == []
    mock_get.assert_not_called()


def test_skips_zero_rest_items():
    crawler = MeatboxCrawler()
    sold_out_item = {**SAMPLE_ITEM_1, "restAmount": 0}
    with patch("crawlers.meatbox.requests.post") as mock_post, \
         patch("crawlers.meatbox.requests.get") as mock_get:
        mock_post.return_value = mock_search_response([SAMPLE_PRODUCT])
        mock_get.return_value = mock_items_response([sold_out_item])

        results = crawler.fetch()

    assert results == []


def test_fetch_returns_empty_on_search_error():
    crawler = MeatboxCrawler()
    with patch("crawlers.meatbox.requests.post") as mock_post:
        mock_post.side_effect = Exception("API 오류")
        results = crawler.fetch()

    assert results == []


def test_fetch_skips_product_on_items_error():
    crawler = MeatboxCrawler()
    with patch("crawlers.meatbox.requests.post") as mock_post, \
         patch("crawlers.meatbox.requests.get") as mock_get:
        mock_post.return_value = mock_search_response([SAMPLE_PRODUCT])
        mock_get.side_effect = Exception("items API 오류")

        results = crawler.fetch()

    assert results == []


def test_url_contains_product_seq():
    crawler = MeatboxCrawler()
    with patch("crawlers.meatbox.requests.post") as mock_post, \
         patch("crawlers.meatbox.requests.get") as mock_get:
        mock_post.return_value = mock_search_response([SAMPLE_PRODUCT])
        mock_get.return_value = mock_items_response([SAMPLE_ITEM_1])

        results = crawler.fetch()

    assert "336499" in results[0].url
    assert "meatbox.co.kr" in results[0].url
