import logging
import re
import requests
from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler, CrawlResult

logger = logging.getLogger(__name__)

SITE_NAME = "일품한우"
BASE_URL  = "https://www.ilpoomhanwoo.com"
LIST_URL  = f"{BASE_URL}/goods/search_list"
PAGE_SIZE = 80

CATEGORIES = {
    "거세": "c0008",
    "암소": "c0022",
}

# 비표준 명칭 → 표준 부위명 (CUT_KEYWORDS 검색 전 우선 확인)
ALIAS_MAP = {
    "꾸리덮개살": "꾸리살",  # 꾸리살 이칭
}

# 수집 제외 (명확하지 않거나 묶음 상품)
EXCLUDE_KEYWORDS = ["갈비모듬육", "모듬육", "청장", "멍에덮개살"]

# 부위 추출 키워드 (구체적 이름 먼저 — 부분 매칭 오분류 방지)
CUT_KEYWORDS = [
    "안심", "윗등심", "등심", "채끝", "목심", "앞다리",
    "꾸리살", "부채살", "우둔", "홍두깨", "설도", "설깃",
    "양지", "사태",
    "앞치마살", "업진안살", "업진살",
    "치마살", "차돌박이", "안창살",
    "제비추리", "토시살",
    "갈비살", "갈비",
]

# "1++(7)[냉장]" 형식도 처리 — 마블링 점수 괄호 허용
GRADE_PATTERN = re.compile(r'(1\+\+|1\+|[123])\s*(?:\(\d+\)\s*)?(?:등급|\[)')

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": BASE_URL,
}


class IlpoomCrawler(BaseCrawler):
    def fetch(self) -> list[CrawlResult]:
        results = []
        for gender, cat in CATEGORIES.items():
            try:
                results.extend(self._fetch_category(gender, cat))
            except Exception as e:
                logger.error(f"[{SITE_NAME}] {gender} 카테고리 실패: {e}")
        return results

    def _fetch_category(self, gender: str, cat: str) -> list[CrawlResult]:
        results = []
        page = 1
        while True:
            resp = requests.get(
                LIST_URL,
                params={"page": page, "searchMode": "catalog", "category": cat,
                        "per": PAGE_SIZE, "sorting": "date", "filter_display": "lattice"},
                headers=HEADERS, timeout=15,
            )
            resp.raise_for_status()
            html = resp.text
            soup = BeautifulSoup(html, "html.parser")
            item_count = len(soup.select("li.goods_price_area"))
            if item_count == 0:
                break
            results.extend(self._parse(html, gender))
            if item_count < PAGE_SIZE:
                break
            page += 1
        return results

    def _parse(self, html: str, gender: str) -> list[CrawlResult]:
        soup = BeautifulSoup(html, "html.parser")
        results = []

        for price_li in soup.select("li.goods_price_area"):
            price_text = price_li.get_text(strip=True)
            if "kg당" not in price_text:
                continue

            parent = price_li.find_parent("ul") or price_li.find_parent("div")
            if not parent:
                continue

            name_tag = parent.select_one("span.name")
            link_tag = parent.select_one("a[href*='/goods/view']")
            if not name_tag or not link_tag:
                continue

            name = name_tag.text.strip()
            if any(ex in name for ex in EXCLUDE_KEYWORDS):
                continue

            cut = self._extract_cut(name)
            if not cut:
                continue

            grade = self._extract_grade(name)
            storage = self._extract_storage(name)
            r = self._parse_item(price_text, link_tag.get("href", ""), gender, cut, grade, storage)
            if r:
                results.append(r)

        return results

    def _extract_cut(self, name: str) -> str | None:
        for alias, cut in ALIAS_MAP.items():
            if alias in name:
                return cut
        for cut in CUT_KEYWORDS:
            if cut in name:
                return cut
        return None

    def _extract_storage(self, name: str) -> str:
        return "냉동" if "냉동" in name else "냉장"

    def _extract_grade(self, name: str) -> str:
        m = GRADE_PATTERN.search(name)
        if m:
            return f"{m.group(1)}등급"
        return "미확인"

    def _parse_item(self, price_text: str, href: str, gender: str, cut: str, grade: str, storage: str = "냉장") -> CrawlResult | None:
        try:
            price_match  = re.search(r"kg당\s*([\d,]+)\s*원", price_text)
            weight_match = re.search(r"원\s*/\s*([\d.]+)\s*kg", price_text)

            if not price_match or not weight_match:
                return None

            price_per_kg = int(price_match.group(1).replace(",", ""))
            weight_kg    = float(weight_match.group(1))

            if not self._is_valid_price(price_per_kg, weight_kg):
                return None

            url = BASE_URL + href if href.startswith("/") else href

            return CrawlResult(
                site=SITE_NAME,
                grade=grade,
                cut=cut,
                gender=gender,
                price_per_kg=price_per_kg,
                weight_kg=weight_kg,
                url=url,
                storage=storage,
            )
        except Exception as e:
            logger.warning(f"[{SITE_NAME}] 파싱 실패: {e}")
            return None
