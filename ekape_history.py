"""
ekapepia.com 한우 식육포장가격 히스토리 크롤러
- 등급별 / 부위별 월간 가격 데이터 수집
- requests + BeautifulSoup (Playwright 불필요)
"""

import sqlite3
import logging
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "https://www.ekapepia.com/v3/price/livestock/cow/wholesale/packingPrice/part.do"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Content-Type": "application/x-www-form-urlencoded",
    "Referer": BASE_URL,
}

# 등급 코드
GRADE_CODES = {
    "1++(평균)": "01",
    "1+":       "02",
    "1":        "03",
    "2":        "04",
    "3":        "05",
}

# 부위 순서 (헤더 기준)
CUT_ORDER = ["안심","등심","채끝","목심","앞다리","설도","양지","사태","갈비","토시살","안창살","제비추리","우둔"]


def init_db():
    conn = sqlite3.connect(config.DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ekape_prices (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            year_month   TEXT NOT NULL,
            grade        TEXT NOT NULL,
            cut          TEXT NOT NULL,
            price_per_kg INTEGER,
            source       TEXT DEFAULT 'ekape',
            UNIQUE(year_month, grade, cut)
        )
    """)
    conn.commit()
    conn.close()
    logger.info("ekape_prices 테이블 준비 완료")


def save_rows(rows: list[dict]) -> int:
    conn = sqlite3.connect(config.DB_PATH)
    saved = 0
    for r in rows:
        try:
            conn.execute("""
                INSERT OR IGNORE INTO ekape_prices (year_month, grade, cut, price_per_kg)
                VALUES (?, ?, ?, ?)
            """, (r["year_month"], r["grade"], r["cut"], r["price_per_kg"]))
            saved += 1
        except Exception as e:
            logger.warning(f"저장 실패: {r} — {e}")
    conn.commit()
    conn.close()
    return saved


def fetch_grade(grade: str, grade_code: str, start_ym: str, end_ym: str) -> list[dict]:
    """특정 등급의 기간별 부위 가격 수집"""
    data = {
        "searchType":      "month",
        "searchCondition": grade_code,
        "searchStartDate": start_ym,   # YYYYMM
        "searchEndDate":   end_ym,
        "startYYMM":       start_ym,
        "endYYMM":         end_ym,
    }

    try:
        resp = requests.post(BASE_URL, data=data, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"[{grade}] 요청 실패: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    tables = soup.find_all("table")
    if not tables:
        logger.warning(f"[{grade}] 테이블 없음")
        return []

    t = tables[0]
    all_rows = t.find_all("tr")

    # 헤더에서 부위 순서 확인
    header_cells = [c.get_text(strip=True) for c in all_rows[0].find_all(["th", "td"])]
    cut_indices = {}
    for i, h in enumerate(header_cells):
        if h in CUT_ORDER:
            cut_indices[i] = h

    if not cut_indices:
        # 헤더 매칭 실패 시 기본 순서 사용 (첫 컬럼=날짜, 이후 CUT_ORDER 순)
        cut_indices = {i+1: cut for i, cut in enumerate(CUT_ORDER)}
        logger.warning(f"[{grade}] 헤더 매칭 실패, 기본 순서 사용. 헤더: {header_cells[:5]}")

    results = []
    for row in all_rows[1:]:
        cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
        if not cells or len(cells) < 2:
            continue

        # 날짜 파싱: '24년 12월' → '2024-12'
        date_raw = cells[0]
        year_month = parse_date(date_raw)
        if not year_month:
            continue

        for idx, cut in cut_indices.items():
            if idx < len(cells):
                price_str = cells[idx].replace(",", "").strip()
                if price_str and price_str != "-":
                    try:
                        results.append({
                            "year_month":   year_month,
                            "grade":        grade,
                            "cut":          cut,
                            "price_per_kg": int(float(price_str)),
                        })
                    except ValueError:
                        pass

    logger.info(f"[{grade}] {len(results)}건 파싱 ({start_ym}~{end_ym})")
    return results


def parse_date(raw: str) -> str | None:
    """'24년 12월' → '2024-12', '2024/01' → '2024-01'"""
    raw = raw.strip()
    # '24년 12월' 형식
    if "년" in raw and "월" in raw:
        parts = raw.replace("년", "").replace("월", "").split()
        if len(parts) == 2:
            yy, mm = parts[0].strip(), parts[1].strip()
            year = f"20{yy}" if len(yy) == 2 else yy
            return f"{year}-{mm.zfill(2)}"
    # '2024/01' 또는 '2024-01' 형식
    raw = raw.replace("/", "-").replace(".", "-")
    if len(raw) >= 7 and raw[4] == "-":
        return raw[:7]
    return None


def run(start_year: int = 2019):
    init_db()
    total = 0

    end_ym   = datetime.now().strftime("%Y%m")
    start_ym = f"{start_year}01"

    logger.info(f"ekape 히스토리 수집 시작: {start_ym} ~ {end_ym}")

    for grade, code in GRADE_CODES.items():
        rows = fetch_grade(grade, code, start_ym, end_ym)
        if rows:
            saved = save_rows(rows)
            total += saved
            logger.info(f"[{grade}] {saved}건 저장")
        else:
            logger.warning(f"[{grade}] 수집 결과 없음")
        time.sleep(1.5)  # 서버 부하 방지

    logger.info(f"✅ 전체 완료 — 총 {total}건 저장")
    print(f"\n✅ ekape 히스토리 수집 완료: {total}건")
    return total


if __name__ == "__main__":
    run(start_year=2019)
