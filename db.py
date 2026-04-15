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
            crawled_at DATETIME NOT NULL
        )
    """)
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
        INSERT INTO prices (site, grade, cut, gender, price_per_kg, weight_kg, url, crawled_at)
        VALUES (:site, :grade, :cut, :gender, :price_per_kg, :weight_kg, :url, :crawled_at)
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

def set_alert_active(active: bool):
    conn = get_conn()
    conn.execute("UPDATE alert_config SET active = ?", (int(active),))
    conn.commit()
    conn.close()
