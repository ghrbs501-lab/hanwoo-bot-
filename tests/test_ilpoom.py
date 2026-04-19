import pytest
from unittest.mock import patch, MagicMock
from crawlers.ilpoom import IlpoomCrawler
from crawlers.base import CrawlResult

SAMPLE_HTML = """
<ul class="item_info_area">
    <li class="goods_name_area">
        <a href="/goods/view?no=3583680"><span class="name">한우알목심/암소/2[냉장]</span></a>
    </li>
    <li class="goods_price_area">
        <span class="sale_price">
            kg당 <b class="num">27,053</b>원 / 4.50kg
        </span>
    </li>
</ul>
<ul class="item_info_area">
    <li class="goods_name_area">
        <a href="/goods/view?no=3583681"><span class="name">한우알목심/암소/2[냉장]</span></a>
    </li>
    <li class="goods_price_area">
        <span class="sale_price">
            kg당 <b class="num">27,053</b>원 / 5.20kg
        </span>
    </li>
</ul>
<ul class="item_info_area">
    <li class="goods_name_area">
        <a href="/goods/view?no=3583999"><span class="name">한우등심/암소/2[냉장]</span></a>
    </li>
    <li class="goods_price_area">
        <span class="sale_price">
            kg당 <b class="num">55,000</b>원 / 8.00kg
        </span>
    </li>
</ul>
<ul class="item_info_area">
    <li class="goods_name_area">
        <a href="/goods/view?no=3578462"><span class="name">한우알목심/거세/1++(7)[냉장]</span></a>
    </li>
    <li class="goods_price_area">
        <span class="sale_price">
            kg당 <b class="num">40,000</b>원 / 6.00kg
        </span>
    </li>
</ul>
"""


def mock_response(html):
    mock = MagicMock()
    mock.status_code = 200
    mock.raise_for_status = MagicMock()
    mock.text = html
    return mock


def test_fetch_returns_crawl_results():
    crawler = IlpoomCrawler()
    with patch("crawlers.ilpoom.requests.get") as mock_get:
        mock_get.return_value = mock_response(SAMPLE_HTML)
        results = crawler.fetch()
    assert len(results) > 0
    assert all(isinstance(r, CrawlResult) for r in results)


def test_filters_only_moksim_grade2():
    crawler = IlpoomCrawler()
    with patch("crawlers.ilpoom.requests.get") as mock_get:
        mock_get.return_value = mock_response(SAMPLE_HTML)
        results = crawler.fetch()
    # 등심과 1++목심은 제외
    for r in results:
        assert r.cut == "목심"
        assert r.grade == "2등급"


def test_price_per_kg_parsed():
    crawler = IlpoomCrawler()
    with patch("crawlers.ilpoom.requests.get") as mock_get:
        mock_get.return_value = mock_response(SAMPLE_HTML)
        results = crawler.fetch()
    prices = {r.price_per_kg for r in results}
    assert 27053 in prices


def test_weight_kg_parsed():
    crawler = IlpoomCrawler()
    with patch("crawlers.ilpoom.requests.get") as mock_get:
        mock_get.return_value = mock_response(SAMPLE_HTML)
        results = crawler.fetch()
    weights = {r.weight_kg for r in results}
    assert 4.5 in weights
    assert 5.2 in weights


def test_gender_암소():
    crawler = IlpoomCrawler()
    with patch("crawlers.ilpoom.requests.get") as mock_get:
        mock_get.return_value = mock_response(SAMPLE_HTML)
        results = crawler.fetch()
    # c0022(암소) 카테고리에서 나온 결과는 암소
    암소_results = [r for r in results if r.gender == "암소"]
    assert len(암소_results) > 0


def test_url_contains_domain():
    crawler = IlpoomCrawler()
    with patch("crawlers.ilpoom.requests.get") as mock_get:
        mock_get.return_value = mock_response(SAMPLE_HTML)
        results = crawler.fetch()
    for r in results:
        assert "ilpoomhanwoo.com" in r.url


def test_fetch_returns_empty_on_error():
    crawler = IlpoomCrawler()
    with patch("crawlers.ilpoom.requests.get") as mock_get:
        mock_get.side_effect = Exception("네트워크 오류")
        results = crawler.fetch()
    assert results == []
