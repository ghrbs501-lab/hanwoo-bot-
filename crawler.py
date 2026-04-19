import logging
import logging.handlers
import config
import db
import alert
from crawlers.geumcheon import GeumcheonCrawler
from crawlers.meatbox import MeatboxCrawler
from crawlers.ilpoom import IlpoomCrawler
from crawlers.topmeat import TopMeatCrawler

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

CRAWLERS = [
    GeumcheonCrawler(),
    MeatboxCrawler(),
    IlpoomCrawler(),
    TopMeatCrawler(),
]

# 사이트별 연속 실패 횟수 추적
_fail_counts: dict[str, int] = {}


def run():
    db.init_db()
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
        items = crawler.to_dict(results)
        all_items.extend(items)
        logger.info(f"[{site}] {len(items)}개 수집")

    if all_items:
        try:
            db.save_prices(all_items)
            logger.info(f"총 {len(all_items)}개 저장 완료")
        except Exception as e:
            logger.error(f"DB 저장 실패: {e}")
            return

    prices = db.get_latest_prices()
    config_row = db.get_alert_config()
    alert.check_and_notify(prices, config_row)


if __name__ == "__main__":
    run()
