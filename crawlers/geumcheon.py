import re
import logging
from playwright.sync_api import sync_playwright
from crawlers.base import BaseCrawler, CrawlResult

logger = logging.getLogger(__name__)

SITE_NAME = "금천미트"
BASE_URL = "https://www.ekcm.co.kr"

CATEGORY_URLS = {
    "거세": f"{BASE_URL}/pd/product?dispCtgNo=13&uprTopDispCtgNo=1&dispCtgNm=%EA%B5%AD%EB%82%B4%EC%82%B0%20%ED%95%9C%EC%9A%B0%20%EA%B1%B0%EC%84%B8&leafCtgNo=130104&dispCtgNoList=130104,130204,130304,130404,130504,130604,130704,130804,815885,816997,817767",
    "암소": f"{BASE_URL}/pd/product?dispCtgNo=14&uprTopDispCtgNo=1&dispCtgNm=%EA%B5%AD%EB%82%B4%EC%82%B0%20%ED%95%9C%EC%9A%B0%20%EC%95%94%EC%86%8C&leafCtgNo=140104&dispCtgNoList=140104,140204,140304,140504,140604,140704,811369,815915,817049,817797",
}

class GeumcheonCrawler(BaseCrawler):
    def fetch(self) -> list[CrawlResult]:
        results = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                for gender, url in CATEGORY_URLS.items():
                    try:
                        page = browser.new_page()
                        page.goto(url, timeout=20000)
                        page.wait_for_load_state("networkidle", timeout=15000)
                        results.extend(self._parse(page, gender))
                        page.close()
                    except Exception as e:
                        logger.error(f"[{SITE_NAME}] {gender} 페이지 크롤링 실패: {e}")
                browser.close()
        except Exception as e:
            logger.error(f"[{SITE_NAME}] Playwright 실행 실패: {e}")
        return results

    def _parse(self, page, gender: str) -> list[CrawlResult]:
        results = []
        products = page.query_selector_all("a[href*='goodsNo']")
        for product in products:
            try:
                grade_el = product.query_selector(".chip.type1")
                price_el = product.query_selector(".pd-price.c-primary")
                weight_el = product.query_selector(".chip-weight")

                grade_text = grade_el.inner_text().strip() if grade_el else ""
                if not grade_text.startswith("2"):
                    continue

                price_text = price_el.inner_text().strip() if price_el else ""
                weight_text = weight_el.inner_text().strip() if weight_el else ""
                href = BASE_URL + product.get_attribute("href")

                price = int(re.sub(r"[^\d]", "", price_text)) if price_text else 0
                weight = float(re.sub(r"[^\d.]", "", weight_text)) if weight_text else 0.0

                if price == 0 or weight == 0.0:
                    continue

                results.append(CrawlResult(
                    site=SITE_NAME,
                    grade="2등급",
                    cut="목심",
                    gender=gender,
                    price_per_kg=price,
                    weight_kg=weight,
                    url=href,
                ))
            except Exception as e:
                logger.warning(f"[{SITE_NAME}] 아이템 파싱 실패: {e}")
        return results
