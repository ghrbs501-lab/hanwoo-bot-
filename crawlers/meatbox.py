import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from crawlers.base import BaseCrawler, CrawlResult

logger = logging.getLogger(__name__)

SITE_NAME = "미트박스"
SEARCH_URL = "https://mb-api.meatbox.co.kr/product/api/v1/search/filter"
ITEMS_URL  = "https://mb-api.meatbox.co.kr/product/api/v1/items/{}/retrieves"
PRODUCT_URL = "https://www.meatbox.co.kr/fo/product/productViewPage.do?productSeq={}"

MAX_WORKERS = 20

# 성별별 catCd → 부위명 (각 성별마다 코드 체계가 다름)
GENDER_CATS = {
    10000: {  # 암소
        "271": "안심",    "241": "등심",    "311": "윗등심",  "202": "채끝",
        "264": "목심",    "272": "앞다리",  "362": "꾸리살",  "265": "부채살",
        "277": "우둔",    "288": "홍두깨",  "270": "설도",    "269": "설깃",
        "274": "양지",    "268": "사태",    "275": "업진살",  "284": "치마살",
        "566": "앞치마살","565": "업진안살","283": "차돌박이","282": "제비추리",
        "285": "토시살",  "243": "안창살",  "262": "갈비살",  "261": "갈비",
    },
    10001: {  # 거세
        "150": "안심",    "149": "등심",    "314": "윗등심",  "151": "채끝",
        "154": "목심",    "152": "앞다리",  "363": "꾸리살",  "155": "부채살",
        "164": "우둔",    "163": "홍두깨",  "156": "설도",    "157": "설깃",
        "158": "양지",    "153": "사태",    "159": "업진살",  "178": "치마살",
        "569": "앞치마살","568": "업진안살","166": "차돌박이","161": "제비추리",
        "160": "토시살",  "324": "안창살",  "246": "갈비살",  "430": "갈비",
    },
    10002: {  # 수소
        "3353": "채끝",   "3356": "부채살", "3361": "차돌박이","3365": "안창살",
    },
}

GENDER_NAMES = {10000: "암소", 10001: "거세", 10002: "수소"}

GENDER_MAP = {
    "한우암소": "암소", "한우거세": "거세", "한우수소": "수소",
}

HEADERS = {
    "Content-Type": "application/json",
    "Referer": "https://www.meatbox.co.kr/",
    "Origin": "https://www.meatbox.co.kr",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
}


class MeatboxCrawler(BaseCrawler):
    def fetch(self) -> list[CrawlResult]:
        # Step 1: 카테고리별 상품 목록 병렬 수집
        cat_tasks = [
            (seq, cat_cd, cut_name)
            for seq, cats in GENDER_CATS.items()
            for cat_cd, cut_name in cats.items()
        ]

        product_tasks = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(self._fetch_products, cat_cd, seq): (seq, cut_name)
                for seq, cat_cd, cut_name in cat_tasks
            }
            for future in as_completed(futures):
                seq, cut_name = futures[future]
                default_gender = GENDER_NAMES[seq]
                try:
                    products = future.result()
                    for product in products:
                        if "육우" in product.get("itemKindName", ""):
                            continue
                        product_tasks.append((product, default_gender, cut_name))
                except Exception as e:
                    logger.error(f"[{SITE_NAME}] {default_gender} {cut_name} 실패: {e}")

        # Step 2: 상품별 아이템 병렬 수집
        results = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(self._fetch_items, product["productSeq"]): (product, default_gender, cut_name)
                for product, default_gender, cut_name in product_tasks
            }
            for future in as_completed(futures):
                product, default_gender, cut_name = futures[future]
                product_seq = product["productSeq"]
                gender = GENDER_MAP.get(product.get("itemKindName", ""), default_gender)
                cattle = product.get("itemCattleInfo", {}) or {}
                qgrade = cattle.get("qgrade", "")
                grade = f"{qgrade}등급" if qgrade else "미확인"
                url = PRODUCT_URL.format(product_seq)
                storage = self._infer_storage(product)
                try:
                    items = future.result()
                    for item in items:
                        r = self._parse_item(item, grade, gender, cut_name, url, storage)
                        if r:
                            results.append(r)
                except Exception as e:
                    logger.warning(f"[{SITE_NAME}] {product_seq} 아이템 조회 실패: {e}")

        return results

    def _infer_storage(self, product: dict) -> str:
        name = product.get("productName", "")
        return "냉동" if "냉동" in name else "냉장"

    def _fetch_products(self, cat_cd: str, seq: int) -> list[dict]:
        resp = requests.post(
            f"{SEARCH_URL}?page=1&size=100",
            json={"displayCategorySeq": [seq], "operator": "or", "itemCatCd": cat_cd},
            headers=HEADERS, timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["data"]["search"]["items"]

    def _fetch_items(self, product_seq: int) -> list[dict]:
        resp = requests.get(ITEMS_URL.format(product_seq), headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.json()["data"]["sortedPricePerKgItems"]

    def _parse_item(self, item: dict, grade: str, gender: str, cut: str, url: str, storage: str = "냉장") -> CrawlResult | None:
        try:
            avg_kg = float(item.get("avgKg") or 0)
            price_per_kg = int(item.get("finalPricePerKg") or 0)

            if not self._is_valid_price(price_per_kg, avg_kg):
                return None
            if int(item.get("restAmount") or 0) <= 0:
                return None

            return CrawlResult(
                site=SITE_NAME,
                grade=grade,
                cut=cut,
                gender=gender,
                price_per_kg=price_per_kg,
                weight_kg=avg_kg,
                url=url,
                storage=storage,
            )
        except Exception as e:
            logger.warning(f"[{SITE_NAME}] 파싱 실패: {e}")
            return None
