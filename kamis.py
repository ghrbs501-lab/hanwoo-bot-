"""
KAMIS (농산물유통정보) API 연동
- 한우 부위별 도매/소매 일별 가격 이력 수집
- API 키: config.py의 KAMIS_API_KEY
"""

import requests
import logging
from datetime import datetime, timedelta
import sqlite3
import config

logger = logging.getLogger(__name__)

BASE_URL = "https://www.kamis.or.kr/service/price/xml.do"

# KAMIS 한우 품목 코드
# 도매: 한우(거세) 코드
ITEM_CODES = {
    "등심":  "810",
    "갈비":  "811",
    "안심":  "812",
    "불고기": "813",
    "앞다리": "814",
}

CATEGORY_CODE = "100"  # 축산물


def fetch_daily_price(
    item_code: str,
    start_date: str,  # "2023-01-01"
    end_date: str,    # "2024-12-31"
    convert_kg: bool = True,
) -> list[dict]:
    """
    KAMIS 일별 가격 조회
    반환: [{"date": "2024-01-01", "price": 45000, "unit": "100g"}, ...]
    """
    params = {
        "action":       "dailyPriceByCategoryList",
        "apikey":       config.KAMIS_API_KEY,
        "regday":       end_date.replace("-", "/"),
        "startday":     start_date.replace("-", "/"),
        "itemcategorycode": CATEGORY_CODE,
        "itemcode":     item_code,
        "kindcode":     "01",   # 상품
        "productrankcode": "04", # 도매
        "countrycode":  "",
        "convert_kg_yn": "Y" if convert_kg else "N",
        "returntype":   "json",
    }

    try:
        resp = requests.get(BASE_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        error = data.get("data", {}).get("error_code")
        if error and error != "000":
            logger.error(f"KAMIS API 에러: {error}")
            return []

        items = data.get("data", {}).get("item", [])
        results = []
        for item in items:
            price_str = item.get("price", "").replace(",", "").strip()
            if not price_str or price_str == "-":
                continue
            try:
                results.append({
                    "date":      item.get("regday", "").replace("/", "-"),
                    "price":     int(price_str),
                    "unit":      item.get("unit", ""),
                    "item_name": item.get("itemname", ""),
                    "kind_name": item.get("kindname", ""),
                })
            except ValueError:
                continue

        logger.info(f"KAMIS [{item_code}] {len(results)}건 수집 ({start_date} ~ {end_date})")
        return results

    except Exception as e:
        logger.error(f"KAMIS 요청 실패: {e}")
        return []


def fetch_all_history(years: int = 3) -> dict[str, list[dict]]:
    """
    전체 부위 과거 데이터 수집
    years: 몇 년치 가져올지
    """
    end   = datetime.today()
    start = end - timedelta(days=365 * years)

    result = {}
    for cut, code in ITEM_CODES.items():
        rows = fetch_daily_price(
            item_code=code,
            start_date=start.strftime("%Y-%m-%d"),
            end_date=end.strftime("%Y-%m-%d"),
        )
        result[cut] = rows

    return result


def save_history_to_db(history: dict[str, list[dict]]):
    """수집한 KAMIS 데이터를 DB에 저장"""
    conn = sqlite3.connect(config.DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS kamis_prices (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date        TEXT NOT NULL,
            cut         TEXT NOT NULL,
            price_per_kg INTEGER NOT NULL,
            unit        TEXT,
            source      TEXT DEFAULT 'kamis',
            UNIQUE(date, cut)
        )
    """)

    total = 0
    for cut, rows in history.items():
        for r in rows:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO kamis_prices (date, cut, price_per_kg, unit)
                    VALUES (?, ?, ?, ?)
                """, (r["date"], cut, r["price"], r["unit"]))
                total += 1
            except Exception as e:
                logger.warning(f"저장 실패: {e}")

    conn.commit()
    conn.close()
    logger.info(f"KAMIS 총 {total}건 저장 완료")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    if not getattr(config, "KAMIS_API_KEY", ""):
        print("❌ config.py에 KAMIS_API_KEY가 없습니다.")
        print("   .env 파일에 KAMIS_API_KEY=발급받은키 추가 후 재실행하세요.")
        exit(1)

    print("📡 KAMIS 3년치 데이터 수집 시작...")
    history = fetch_all_history(years=3)
    save_history_to_db(history)
    print("✅ 완료!")
