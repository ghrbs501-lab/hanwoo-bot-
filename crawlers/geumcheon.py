import math
import logging
import requests
from crawlers.base import BaseCrawler, CrawlResult

logger = logging.getLogger(__name__)

SITE_NAME = "금천미트"
API_URL = "https://gw.ekcm.co.kr/api/goods/v1/goods/dispGoodsList"
PRODUCT_URL = "https://www.ekcm.co.kr/pd/productDetail?goodsNo={}"
PAGE_SIZE = 30

CATEGORIES = {
    "거세": {
        "dispCtgNoList": ["130104","130204","130304","130404","130504","130604","130704","130804","815885","816997","817767"],
        "curCtgNo": "130104",
    },
    "암소": {
        "dispCtgNoList": ["140104","140204","140304","140504","140604","140704","811369","815915","817049","817797"],
        "curCtgNo": "140104",
    },
}

HEADERS = {
    "Content-Type": "application/json",
    "Referer": "https://www.ekcm.co.kr/",
    "Origin": "https://www.ekcm.co.kr",
    "User-Agent": "Mozilla/5.0",
}


class GeumcheonCrawler(BaseCrawler):
    def fetch(self) -> list[CrawlResult]:
        results = []
        for gender, cat in CATEGORIES.items():
            try:
                results.extend(self._fetch_category(gender, cat))
            except Exception as e:
                logger.error(f"[{SITE_NAME}] {gender} 카테고리 실패: {e}")
        return results

    def _fetch_category(self, gender: str, cat: dict) -> list[CrawlResult]:
        results = []
        page_no = 1
        total = None

        while True:
            payload = {
                "dispCtgNoList": cat["dispCtgNoList"],
                "brandNoList": [], "lsprdGrdCdList": ["2"],
                "homeCdList": [], "ppYmdList": [], "strgMthdGbCdList": [],
                "workMethTypCdList": [], "deliProcTypCdList": [], "recomBkindList": [],
                "qualityList": [], "insfatGrdList": [], "mffldList": [], "estNoList": [],
                "sortTpCd": "10", "pageNo": page_no, "pageSize": PAGE_SIZE,
                "aplyPsbMediaCd": "01", "curCtgNo": cat["curCtgNo"],
                "noDispCtgRegYn": "N", "mbrNo": "",
            }
            resp = requests.post(API_URL, json=payload, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("payload", [])

            if not items:
                break

            if total is None:
                total = items[0].get("totCnt", 0)
                logger.info(f"[{SITE_NAME}] {gender} 2등급 목심 총 {total}개")

            for item in items:
                result = self._parse_item(item, gender)
                if result:
                    results.append(result)

            if len(results) >= total or len(items) < PAGE_SIZE:
                break

            page_no += 1

        return results

    def _parse_item(self, item: dict, gender: str) -> CrawlResult | None:
        try:
            wgt = float(item.get("invtWgt") or 0)
            price_total = int(item.get("salePrc") or 0)
            if wgt <= 0 or price_total <= 0:
                return None

            price_per_kg = round(price_total / wgt)
            goods_no = item["goodsNo"]
            quality = item.get("korthsMwgtGrdCd", "")  # A/B/C

            return CrawlResult(
                site=SITE_NAME,
                grade=f"2등급{quality}",
                cut="목심",
                gender=gender,
                price_per_kg=price_per_kg,
                weight_kg=float(wgt),
                url=PRODUCT_URL.format(goods_no),
            )
        except Exception as e:
            logger.warning(f"[{SITE_NAME}] 아이템 파싱 실패: {e}")
            return None
