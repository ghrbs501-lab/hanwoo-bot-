import sqlite3
import config

DB_PATH = config.DB_PATH

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site TEXT NOT NULL,
            grade TEXT NOT NULL,
            cut TEXT NOT NULL,
            gender TEXT NOT NULL,
            price_per_kg INTEGER NOT NULL,
            weight_kg REAL NOT NULL,
            url TEXT NOT NULL,
            crawled_at DATETIME NOT NULL,
            storage TEXT NOT NULL DEFAULT '냉장'
        )
    """)
    # 기존 DB에 컬럼 없을 경우 추가
    cols = [r[1] for r in conn.execute("PRAGMA table_info(prices)").fetchall()]
    if "storage" not in cols:
        conn.execute("ALTER TABLE prices ADD COLUMN storage TEXT NOT NULL DEFAULT '냉장'")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alert_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cut TEXT NOT NULL,
            grade TEXT NOT NULL,
            target_price INTEGER NOT NULL,
            active BOOLEAN NOT NULL DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()

def save_prices(items: list[dict]):
    conn = get_conn()
    conn.executemany("""
        INSERT INTO prices (site, grade, cut, gender, price_per_kg, weight_kg, url, crawled_at, storage)
        VALUES (:site, :grade, :cut, :gender, :price_per_kg, :weight_kg, :url, :crawled_at, :storage)
    """, items)
    conn.commit()
    conn.close()

def get_latest_prices() -> list[dict]:
    """각 사이트별 가장 최근 크롤링 결과만 반환"""
    conn = get_conn()
    rows = conn.execute("""
        SELECT p.*
        FROM prices p
        INNER JOIN (
            SELECT site, MAX(crawled_at) AS max_at
            FROM prices
            GROUP BY site
        ) latest ON p.site = latest.site AND p.crawled_at = latest.max_at
        ORDER BY p.price_per_kg ASC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_prices_above_weight(min_weight_kg: float) -> list[dict]:
    """최신 크롤링 결과 중 중량 조건을 만족하는 매물, 가격 오름차순"""
    conn = get_conn()
    rows = conn.execute("""
        SELECT p.*
        FROM prices p
        INNER JOIN (
            SELECT site, MAX(crawled_at) AS max_at
            FROM prices
            GROUP BY site
        ) latest ON p.site = latest.site AND p.crawled_at = latest.max_at
        WHERE p.weight_kg >= ?
        ORDER BY p.price_per_kg ASC
    """, (min_weight_kg,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_alert_config() -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM alert_config ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return dict(row) if row else None

def set_alert_config(cut: str, grade: str, target_price: int, active: bool):
    conn = get_conn()
    conn.execute("DELETE FROM alert_config")
    conn.execute("""
        INSERT INTO alert_config (cut, grade, target_price, active)
        VALUES (?, ?, ?, ?)
    """, (cut, grade, target_price, int(active)))
    conn.commit()
    conn.close()

def get_prices_filtered(grade: str = None, cut: str = None, gender: str = None, storage: str = None) -> list[dict]:
    """최신 크롤링 결과에서 조건에 맞는 매물을 사이트별 최저가 순으로 반환"""
    conn = get_conn()
    conditions = ["p.crawled_at = latest.max_at"]
    params = []
    if grade:
        conditions.append("p.grade LIKE ?")
        params.append(f"{grade}%")
    if cut:
        conditions.append("p.cut = ?")
        params.append(cut)
    if gender:
        conditions.append("p.gender = ?")
        params.append(gender)
    if storage:
        conditions.append("p.storage = ?")
        params.append(storage)

    where = " AND ".join(conditions)
    rows = conn.execute(f"""
        SELECT p.*
        FROM prices p
        INNER JOIN (
            SELECT site, MAX(crawled_at) AS max_at
            FROM prices
            GROUP BY site
        ) latest ON p.site = latest.site AND {where}
        ORDER BY p.price_per_kg ASC
    """, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_summary() -> list[dict]:
    """사이트별 최저가 1개씩 반환 (히어로 섹션용)"""
    conn = get_conn()
    rows = conn.execute("""
        SELECT p.*
        FROM prices p
        INNER JOIN (
            SELECT site, MAX(crawled_at) AS max_at
            FROM prices
            GROUP BY site
        ) latest ON p.site = latest.site AND p.crawled_at = latest.max_at
        INNER JOIN (
            SELECT site, MIN(price_per_kg) AS min_price
            FROM prices
            GROUP BY site
        ) cheapest ON p.site = cheapest.site AND p.price_per_kg = cheapest.min_price
        GROUP BY p.site
        ORDER BY p.price_per_kg ASC
        LIMIT 3
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def set_alert_active(active: bool):
    conn = get_conn()
    conn.execute("UPDATE alert_config SET active = ?", (int(active),))
    conn.commit()
    conn.close()
