import re
import logging
from playwright.sync_api import sync_playwright
from crawlers.base import BaseCrawler, CrawlResult

logger = logging.getLogger(__name__)

SITE_NAME = "탑미트"
BASE_URL   = "https://www.topmeat.co.kr"
LIST_URL   = f"{BASE_URL}/shop/list.php"
ITEM_URL   = f"{BASE_URL}/shop/item.php?it_id={{}}"

# ca_id 구조: 1xxx=거세, 2xxx=암소, 3xxx=수소(육우거세)
CATEGORIES = {
    # 거세
    "1010": ("거세", "안심"),    "1020": ("거세", "등심"),
    "1030": ("거세", "채끝"),    "1040": ("거세", "목심"),
    "1050": ("거세", "사태"),    "1060": ("거세", "앞다리"),
    "1061": ("거세", "꾸리살"),  "10l0": ("거세", "부채살"),
    "10y0": ("거세", "우둔"),    "1011": ("거세", "홍두깨"),
    "1080": ("거세", "설도"),    "10a0": ("거세", "설깃"),
    "10b0": ("거세", "양지"),    "10d2": ("거세", "치마살"),
    "10d3": ("거세", "업진살"),  "10d4": ("거세", "안창살"),
    "10f0": ("거세", "갈비"),    "1012": ("거세", "갈비살"),
    "10c0": ("거세", "차돌박이"),
    # 암소
    "2010": ("암소", "안심"),    "2020": ("암소", "등심"),
    "2030": ("암소", "채끝"),    "2040": ("암소", "목심"),
    "2050": ("암소", "사태"),    "2060": ("암소", "앞다리"),
    "2061": ("암소", "꾸리살"),  "20l0": ("암소", "부채살"),
    "2013": ("암소", "우둔"),    "2011": ("암소", "홍두깨"),
    "2080": ("암소", "설도"),    "20a0": ("암소", "설깃"),
    "20b0": ("암소", "양지"),    "20d2": ("암소", "치마살"),
    "20d3": ("암소", "업진살"),  "20d4": ("암소", "안창살"),
    "20f0": ("암소", "갈비"),    "2012": ("암소", "갈비살"),
    "20c0": ("암소", "차돌박이"),
    # 수소(육우거세) — 안창살 카테고리 없음
    "3010": ("수소", "안심"),    "3020": ("수소", "등심"),
    "3030": ("수소", "채끝"),    "3040": ("수소", "목심"),
    "3050": ("수소", "사태"),    "3060": ("수소", "앞다리"),
    "3062": ("수소", "꾸리살"),  "30l0": ("수소", "부채살"),
    "3071": ("수소", "우둔"),    "3072": ("수소", "홍두깨"),
    "3080": ("수소", "설도"),    "30a0": ("수소", "설깃"),
    "30b0": ("수소", "양지"),    "30d5": ("수소", "치마살"),
    "30d3": ("수소", "업진살"),
    "30f0": ("수소", "갈비"),    "30f1": ("수소", "갈비살"),
    "30c0": ("수소", "차돌박이"),
}


class TopMeatCrawler(BaseCrawler):
    def fetch(self) -> list[CrawlResult]:
        results = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                for ca_id, (gender, cut) in CATEGORIES.items():
                    try:
                        page = browser.new_page()
                        results.extend(self._fetch_category(page, gender, cut, ca_id))
                        page.close()
                    except Exception as e:
                        logger.error(f"[{SITE_NAME}] {gender} {cut} 실패: {e}")
                browser.close()
        except Exception as e:
            logger.error(f"[{SITE_NAME}] 크롤링 실패: {e}")
        return results

    def _fetch_category(self, page, gender: str, cut: str, ca_id: str) -> list[CrawlResult]:
        # 등급 필터 없이 전체 조회
        url = f"{LIST_URL}?ca_id={ca_id}&per_page=100"
        page.goto(url, timeout=20000)
        page.wait_for_timeout(2000)
        return self._parse(page.content(), gender, cut)

    def _parse(self, html: str, gender: str, cut: str) -> list[CrawlResult]:
        ids = re.findall(r'name="it_id\[(\d+)\]" value="([^"]+)"', html)
        results = []
        for idx, it_id in ids:
            r = self._parse_item(html, idx, it_id, gender, cut)
            if r:
                results.append(r)
        return results

    def _extract_field(self, html: str, name: str, idx: str) -> str | None:
        m = re.search(rf'name="{re.escape(name)}\[{idx}\]" value="([^"]*)"', html)
        return m.group(1) if m else None

    def _parse_item(self, html: str, idx: str, it_id: str, gender: str, cut: str) -> CrawlResult | None:
        try:
            price_str  = self._extract_field(html, "it_maker2", idx)
            weight_str = self._extract_field(html, "it_origin1", idx)
            grade_str  = self._extract_field(html, "it_maker5", idx)

            if not price_str or not weight_str:
                return None

            price_per_kg = int(price_str.replace(",", ""))
            weight_kg    = float(weight_str)

            if not self._is_valid_price(price_per_kg, weight_kg):
                return None

            grade = f"{grade_str}등급" if grade_str else "미확인"

            name    = self._extract_field(html, "it_name", idx) or ""
            name_1  = self._extract_field(html, "it_name_1", idx) or ""
            storage = "냉동" if "냉동" in name or "냉동" in name_1 else "냉장"

            return CrawlResult(
                site=SITE_NAME,
                grade=grade,
                cut=cut,
                gender=gender,
                price_per_kg=price_per_kg,
                weight_kg=weight_kg,
                url=ITEM_URL.format(it_id),
                storage=storage,
            )
        except Exception as e:
            logger.warning(f"[{SITE_NAME}] 파싱 실패: {e}")
            return None
