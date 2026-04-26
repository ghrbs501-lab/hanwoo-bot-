import asyncio
import logging
import config
import db
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def cmd_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prices = db.get_latest_prices()
    if not prices:
        await update.message.reply_text("수집된 가격 정보가 없습니다. 잠시 후 다시 시도해주세요.")
        return
    # 사이트별 최저가 1개씩만
    seen = {}
    for p in prices:
        if p['site'] not in seen:
            seen[p['site']] = p
    lines = ["📊 사이트별 최저가 매물\n"]
    for p in seen.values():
        lines.append(
            f"📍 {p['site']}\n"
            f"   {p['price_per_kg']:,}원/kg · {p['weight_kg']}kg ({p['gender']})\n"
            f"   👉 {p['url']}\n"
        )
    await update.message.reply_text("\n".join(lines))


async def cmd_best(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prices = db.get_latest_prices()
    if not prices:
        await update.message.reply_text("수집된 가격 정보가 없습니다.")
        return
    best = prices[0]
    msg = (
        f"🥇 현재 최저가 매물\n\n"
        f"📍 {best['site']}\n"
        f"부위: {best['grade']} {best['cut']} ({best['gender']})\n"
        f"가격: {best['price_per_kg']:,}원/kg\n"
        f"중량: {best['weight_kg']}kg\n"
        f"👉 {best['url']}"
    )
    await update.message.reply_text(msg)


async def cmd_recommend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("사용법: /recommend [최소중량kg]\n예: /recommend 50")
        return
    try:
        min_weight = float(context.args[0])
    except ValueError:
        await update.message.reply_text("중량은 숫자로 입력해주세요. 예: /recommend 50")
        return
    prices = db.get_prices_above_weight(min_weight)
    if not prices:
        await update.message.reply_text(f"{min_weight}kg 이상 매물이 없습니다.")
        return
    lines = [f"📦 {min_weight}kg 이상 매물 (가격 순)\n"]
    for i, p in enumerate(prices[:5], 1):
        lines.append(
            f"{i}위 {p['price_per_kg']:,}원/kg — {p['site']} ({p['gender']}, {p['weight_kg']}kg) 👉 {p['url']}"
        )
    await update.message.reply_text("\n".join(lines))


async def cmd_setalert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("사용법: /setalert [목표가]\n예: /setalert 24000")
        return
    try:
        target = int(context.args[0])
    except ValueError:
        await update.message.reply_text("목표가는 숫자로 입력해주세요. 예: /setalert 24000")
        return
    db.set_alert_config(cut="목심", grade="2등급", target_price=target, active=True)
    await update.message.reply_text(
        f"✅ 목표가 설정 완료: {target:,}원/kg\n"
        f"2등급 목심이 이 가격 이하로 나오면 알림을 드립니다."
    )


async def cmd_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = db.get_alert_config()
    if not cfg:
        await update.message.reply_text("설정된 알림이 없습니다. /setalert [가격] 으로 설정하세요.")
        return
    status = "활성" if cfg["active"] else "중지"
    await update.message.reply_text(
        f"🔔 현재 알림 설정\n"
        f"품목: {cfg['grade']} {cfg['cut']}\n"
        f"목표가: {cfg['target_price']:,}원/kg\n"
        f"상태: {status}"
    )


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.set_alert_active(False)
    await update.message.reply_text("🔕 알림을 중지했습니다.")


async def cmd_start_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.set_alert_active(True)
    await update.message.reply_text("🔔 알림을 재개했습니다.")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "안녕하세요! 한우 가격 모니터링 봇입니다 🐄\n\n"
        "명령어 목록:\n"
        "/price — 사이트별 2등급 목심 최저가\n"
        "/best — 현재 절대 최저가 매물\n"
        "/recommend [kg] — 지정 중량 이상 추천\n"
        "/setalert [가격] — 목표가 알림 설정\n"
        "/alert — 현재 알림 설정 확인\n"
        "/stop — 알림 중지\n"
        "/resume — 알림 재개"
    )


async def main():
    db.init_db()
    app = Application.builder().token(config.TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("price", cmd_price))
    app.add_handler(CommandHandler("best", cmd_best))
    app.add_handler(CommandHandler("recommend", cmd_recommend))
    app.add_handler(CommandHandler("setalert", cmd_setalert))
    app.add_handler(CommandHandler("alert", cmd_alert))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("resume", cmd_start_alert))
    logger.info("봇 시작")
    async with app:
        await app.start()
        await app.updater.start_polling()
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
