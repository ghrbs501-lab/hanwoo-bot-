import requests
import logging
import config

logger = logging.getLogger(__name__)


def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }, timeout=10)


def format_alert_message(item: dict, target_price: int) -> str:
    return (
        f"🔔 목표가 이하 매물 발견!\n\n"
        f"📍 {item['site']}\n"
        f"부위: {item['grade']} {item['cut']} ({item['gender']})\n"
        f"가격: {item['price_per_kg']:,}원/kg\n"
        f"중량: {item['weight_kg']}kg\n"
        f"👉 {item['url']}\n\n"
        f"목표가: {target_price:,}원/kg"
    )


def check_and_notify(prices: list[dict], config_row: dict):
    if not config_row or not config_row["active"]:
        return
    target = config_row["target_price"]
    target_cut = config_row["cut"]
    target_grade = config_row["grade"]
    for item in prices:
        if item["cut"] != target_cut or item["grade"] != target_grade:
            continue
        if item["price_per_kg"] <= target:
            msg = format_alert_message(item, target)
            try:
                send_telegram(msg)
                logger.info(f"알림 전송: {item['site']} {item['price_per_kg']}원/kg")
            except Exception as e:
                logger.error(f"텔레그램 전송 실패: {e}")
