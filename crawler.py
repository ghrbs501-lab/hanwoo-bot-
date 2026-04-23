import logging
import logging.handlers
from datetime import datetime, timezone, timedelta
import config
import db
import alert
from crawlers.geumcheon import GeumcheonCrawler
from crawlers.meatbox import MeatboxCrawler
from crawlers.ilpoom import IlpoomCrawler

logging.basicConfig(
    handlers=[
        logging.handlers.RotatingFileHandler(
            config.LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=3
        ),
        logging.StreamHandler(),
    ],
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))

CRAWLERS = [
    GeumcheonCrawler(),
    MeatboxCrawler(),
    IlpoomCrawler(),
]

_fail_counts: dict[str, int] = {}


def _crawl_all() -> list[dict]:
    all_items = []
    for crawler in CRAWLERS:
        site = crawler.__class__.__name__
        results = crawler.fetch()

        if not results:
            _fail_counts[site] = _fail_counts.get(site, 0) + 1
            logger.warning(f"[{site}] 수집 결과 없음 (누적 실패: {_fail_counts[site]})")
            if _fail_counts[site] >= 3:
                try:
                    alert.send_telegram(f"⚠️ {site} 크롤링 3회 연속 실패. 확인 필요.")
                except Exception:
                    pass
            continue

        _fail_counts[site] = 0
        items = [i for i in crawler.to_dict(results) if i.get("grade") != "미확인"]
        all_items.extend(items)
        logger.info(f"[{site}] {len(items)}개 수집")

    return all_items


def run():
    db.init_db()

    now_kst = datetime.now(KST)
    hour = now_kst.hour
    logger.info(f"크롤링 시작 — KST {now_kst.strftime('%H:%M')}")

    if hour == 9:
        # 전날 16시 데이터를 히스토리에 저장 후 교체
        yesterday = (now_kst - timedelta(days=1)).strftime("%Y-%m-%d")
        db.snapshot_daily_lowest(yesterday)
        logger.info(f"[daily_lowest] {yesterday} 스냅샷 저장 완료")

    all_items = _crawl_all()

    if not all_items:
        logger.warning("수집 결과 없음 — prices 테이블 유지")
        return

    try:
        db.replace_current_prices(all_items)
        logger.info(f"총 {len(all_items)}개 저장 완료 (기존 데이터 교체)")
    except Exception as e:
        logger.error(f"DB 저장 실패: {e}")
        return

    prices = db.get_latest_prices()
    config_row = db.get_alert_config()
    alert.check_and_notify(prices, config_row)


if __name__ == "__main__":
    run()
