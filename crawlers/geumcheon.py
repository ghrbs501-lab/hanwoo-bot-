import logging
import requests
from crawlers.base import BaseCrawler, CrawlResult

logger = logging.getLogger(__name__)

SITE_NAME = "금천미트"
API_URL = "https://gw.ekcm.co.kr/api/goods/v1/goods/dispGoodsList"
PRODUCT_URL = "https://www.ekcm.co.kr/pd/productDetail?goodsNo={}"
PAGE_SIZE = 30

# 상품명 교차검증용 키워드 (구체적/긴 이름 먼저 — 부분 매칭 오분류 방지)
VERIFY_KEYWORDS = [
    "앞치마살", "업진안살", "업진살", "치마살",
    "꾸리살", "부채살", "홍두깨", "설깃", "설도",
    "안창살", "제비추리", "토시살", "차돌박이",
    "갈비살", "갈비",
    "안심", "등심", "채끝", "목심", "앞다리",
    "우둔", "양지", "사태",
]

# 부위 코드 (01~19)
CUT_CODES = {
    "01": "안심",   "02": "등심",   "03": "채끝",   "04": "목심",
    "05": "앞다리", "06": "꾸리살", "07": "부채살", "08": "우둔",
    "09": "홍두깨", "10": "설도",   "11": "설깃",   "12": "치마살",
    "13": "업진살", "14": "앞치마살","15": "업진안살","16": "양지",
    "17": "사태",   "18": "갈비",   "19": "갈비살",
    "20": "안창살", "21": "토시살", "22": "제비추리","28": "차돌박이",
}

# 성별 코드 (거세=13, 암소=14)
GENDER_CODES = {
    "거세": "13",
    "암소": "14",
}

# 브랜드별 카테고리 번호 (Xxx 자리)
BRAND_SLOTS = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10"]

HEADERS = {
    "Content-Type": "application/json",
    "Referer": "https://www.ekcm.co.kr/",
    "Origin": "https://www.ekcm.co.kr",
    "User-Agent": "Mozilla/5.0",
}


class GeumcheonCrawler(BaseCrawler):
    def fetch(self) -> list[CrawlResult]:
        results = []
        for gender, gender_code in GENDER_CODES.items():
            for cut_code, cut_name in CUT_CODES.items():
                # 브랜드별 카테고리 목록 조합
                ctg_list = [
                    f"{gender_code}{slot}{cut_code}"
                    for slot in BRAND_SLOTS
                ]
                cur_ctg = ctg_list[0]
                try:
                    items = self._fetch_all(ctg_list, cur_ctg)
                    for item in items:
                        r = self._parse_item(item, gender, cut_name)
                        if r:
                            results.append(r)
                except Exception as e:
                    logger.error(f"[{SITE_NAME}] {gender} {cut_name} 실패: {e}")
        return results

    def _fetch_all(self, ctg_list: list, cur_ctg: str) -> list[dict]:
        results = []
        page_no = 1
        total = None

        while True:
            payload = {
                "dispCtgNoList": ctg_list,
                "brandNoList": [], "lsprdGrdCdList": [],
                "homeCdList": [], "ppYmdList": [], "strgMthdGbCdList": [],
                "workMethTypCdList": [], "deliProcTypCdList": [], "recomBkindList": [],
                "qualityList": [], "insfatGrdList": [], "mffldList": [], "estNoList": [],
                "sortTpCd": "10", "pageNo": page_no, "pageSize": PAGE_SIZE,
                "aplyPsbMediaCd": "01", "curCtgNo": cur_ctg,
                "noDispCtgRegYn": "N", "mbrNo": "",
            }
            resp = requests.post(API_URL, json=payload, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            items = resp.json().get("payload", [])

            if not items:
                break

            if total is None:
                total = items[0].get("totCnt", 0)

            results.extend(items)

            if len(results) >= total or len(items) < PAGE_SIZE:
                break

            page_no += 1

        return results

    def _parse_grade(self, item: dict) -> str:
        # lsprdGrdCd: "1","2","3" = 일반 등급, "A"=1++ 추정
        QGRADE_MAP = {"1": "1", "2": "2", "3": "3", "A": "1++", "B": "1+"}
        qraw   = item.get("lsprdGrdCd", "")
        qgrade = QGRADE_MAP.get(qraw, qraw)
        if qgrade:
            return f"{qgrade}등급"
        return "미확인"

    def _is_correct_cut(self, goods_nm: str, expected_cut: str) -> bool:
        """상품명에서 부위 키워드를 추출해 기대 부위와 일치하는지 확인.
        판매자가 잘못된 카테고리에 등록한 상품을 걸러낸다."""
        for keyword in VERIFY_KEYWORDS:
            if keyword in goods_nm:
                return keyword == expected_cut
        return True  # 부위명 미포함 → 카테고리 분류 신뢰

    def _parse_item(self, item: dict, gender: str, cut: str) -> CrawlResult | None:
        try:
            goods_nm = item.get("goodsNm", "")
            if not self._is_correct_cut(goods_nm, cut):
                logger.debug(f"[{SITE_NAME}] 오분류 제외: {goods_nm!r} (기대={cut})")
                return None

            wgt = float(item.get("invtWgt") or 0)
            price_total = int(item.get("salePrc") or 0)
            price_per_kg = round(price_total / wgt) if wgt > 0 else 0

            if not self._is_valid_price(price_per_kg, wgt):
                return None

            grade = self._parse_grade(item)
            storage = item.get("strgMthdGbNm", "냉장") or "냉장"

            return CrawlResult(
                site=SITE_NAME,
                grade=grade,
                cut=cut,
                gender=gender,
                price_per_kg=price_per_kg,
                weight_kg=float(wgt),
                url=PRODUCT_URL.format(item["goodsNo"]),
                storage=storage,
            )
        except Exception as e:
            logger.warning(f"[{SITE_NAME}] 파싱 실패: {e}")
            return None
