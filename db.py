import psycopg
from psycopg.rows import dict_row
import config


def get_conn():
    return psycopg.connect(config.DATABASE_URL, row_factory=dict_row)


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS prices (
                id SERIAL PRIMARY KEY,
                site TEXT NOT NULL,
                grade TEXT NOT NULL,
                cut TEXT NOT NULL,
                gender TEXT NOT NULL,
                price_per_kg INTEGER NOT NULL,
                weight_kg REAL NOT NULL,
                url TEXT NOT NULL,
                crawled_at TIMESTAMP NOT NULL,
                storage TEXT NOT NULL DEFAULT '냉장'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS alert_config (
                id SERIAL PRIMARY KEY,
                cut TEXT NOT NULL,
                grade TEXT NOT NULL,
                target_price INTEGER NOT NULL,
                active BOOLEAN NOT NULL DEFAULT TRUE
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_lowest (
                id SERIAL PRIMARY KEY,
                recorded_date DATE NOT NULL,
                cut TEXT NOT NULL,
                grade TEXT NOT NULL,
                price_per_kg INTEGER NOT NULL,
                UNIQUE (recorded_date, cut, grade)
            )
        """)


def save_prices(items: list[dict]):
    with get_conn() as conn:
        conn.executemany("""
            INSERT INTO prices (site, grade, cut, gender, price_per_kg, weight_kg, url, crawled_at, storage)
            VALUES (%(site)s, %(grade)s, %(cut)s, %(gender)s, %(price_per_kg)s, %(weight_kg)s, %(url)s, %(crawled_at)s, %(storage)s)
        """, items)


def replace_current_prices(items: list[dict]):
    with get_conn() as conn:
        conn.execute("DELETE FROM prices")
        conn.executemany("""
            INSERT INTO prices (site, grade, cut, gender, price_per_kg, weight_kg, url, crawled_at, storage)
            VALUES (%(site)s, %(grade)s, %(cut)s, %(gender)s, %(price_per_kg)s, %(weight_kg)s, %(url)s, %(crawled_at)s, %(storage)s)
        """, items)


def snapshot_daily_lowest(recorded_date: str):
    """prices 테이블에서 거세우 기준 부위+등급별 최저가를 daily_lowest에 저장 (전날 날짜로)"""
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO daily_lowest (recorded_date, cut, grade, price_per_kg)
            SELECT %s, cut, grade, MIN(price_per_kg)
            FROM prices
            WHERE grade != '미확인'
              AND gender = '거세'
            GROUP BY cut, grade
            ON CONFLICT (recorded_date, cut, grade) DO UPDATE
                SET price_per_kg = EXCLUDED.price_per_kg
        """, (recorded_date,))


def get_latest_prices() -> list[dict]:
    with get_conn() as conn:
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
    return rows


def get_prices_above_weight(min_weight_kg: float) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT p.*
            FROM prices p
            INNER JOIN (
                SELECT site, MAX(crawled_at) AS max_at
                FROM prices
                GROUP BY site
            ) latest ON p.site = latest.site AND p.crawled_at = latest.max_at
            WHERE p.weight_kg >= %s
            ORDER BY p.price_per_kg ASC
        """, (min_weight_kg,)).fetchall()
    return rows


def get_alert_config() -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM alert_config ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return row


def set_alert_config(cut: str, grade: str, target_price: int, active: bool):
    with get_conn() as conn:
        conn.execute("DELETE FROM alert_config")
        conn.execute("""
            INSERT INTO alert_config (cut, grade, target_price, active)
            VALUES (%s, %s, %s, %s)
        """, (cut, grade, target_price, active))


def get_prices_filtered(grade: str = None, cut: str = None, gender: str = None, storage: str = None) -> list[dict]:
    conditions = ["p.crawled_at = latest.max_at"]
    params = []
    if grade:
        conditions.append("p.grade LIKE %s")
        params.append(f"{grade}%")
    if cut:
        conditions.append("p.cut = %s")
        params.append(cut)
    if gender:
        conditions.append("p.gender = %s")
        params.append(gender)
    if storage:
        conditions.append("p.storage = %s")
        params.append(storage)

    where = " AND ".join(conditions)
    with get_conn() as conn:
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
    return rows


def get_summary() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT DISTINCT ON (p.site) p.*
            FROM prices p
            INNER JOIN (
                SELECT site, MAX(crawled_at) AS max_at
                FROM prices
                GROUP BY site
            ) latest ON p.site = latest.site AND p.crawled_at = latest.max_at
            ORDER BY p.site, p.price_per_kg ASC
            LIMIT 3
        """).fetchall()
    return rows


def set_alert_active(active: bool):
    with get_conn() as conn:
        conn.execute("UPDATE alert_config SET active = %s", (active,))


def get_distinct(col: str) -> list:
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT DISTINCT {col} FROM prices ORDER BY {col}"
        ).fetchall()
    return [r[col] for r in rows]
