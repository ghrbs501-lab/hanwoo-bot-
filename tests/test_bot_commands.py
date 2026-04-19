import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_price_command_returns_message():
    from bot import cmd_price
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    with patch("bot.db.get_latest_prices") as mock_prices:
        mock_prices.return_value = [
            {"site": "금천미트", "price_per_kg": 24300, "weight_kg": 10.3,
             "gender": "거세", "grade": "2등급A", "cut": "목심",
             "url": "https://www.ekcm.co.kr/pd/productDetail?goodsNo=1"},
        ]
        await cmd_price(update, context)

    update.message.reply_text.assert_called_once()
    msg = update.message.reply_text.call_args[0][0]
    assert "금천미트" in msg
    assert "24,300" in msg


@pytest.mark.asyncio
async def test_price_command_empty():
    from bot import cmd_price
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    with patch("bot.db.get_latest_prices", return_value=[]):
        await cmd_price(update, context)

    msg = update.message.reply_text.call_args[0][0]
    assert "없습니다" in msg


@pytest.mark.asyncio
async def test_best_command():
    from bot import cmd_best
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    with patch("bot.db.get_latest_prices") as mock_prices:
        mock_prices.return_value = [
            {"site": "탑미트", "price_per_kg": 24010, "weight_kg": 8.9,
             "gender": "암소", "grade": "2등급", "cut": "목심",
             "url": "https://www.topmeat.co.kr/shop/item.php?it_id=123"},
        ]
        await cmd_best(update, context)

    msg = update.message.reply_text.call_args[0][0]
    assert "탑미트" in msg
    assert "24,010" in msg


@pytest.mark.asyncio
async def test_setalert_command_sets_target():
    from bot import cmd_setalert
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = ["24000"]

    with patch("bot.db.set_alert_config") as mock_set:
        await cmd_setalert(update, context)
        mock_set.assert_called_once_with(
            cut="목심", grade="2등급", target_price=24000, active=True
        )


@pytest.mark.asyncio
async def test_setalert_invalid_input():
    from bot import cmd_setalert
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = ["abc"]

    with patch("bot.db.set_alert_config") as mock_set:
        await cmd_setalert(update, context)
        mock_set.assert_not_called()

    msg = update.message.reply_text.call_args[0][0]
    assert "숫자" in msg


@pytest.mark.asyncio
async def test_recommend_command_filters_by_weight():
    from bot import cmd_recommend
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = ["10"]

    with patch("bot.db.get_prices_above_weight") as mock_prices:
        mock_prices.return_value = [
            {"site": "금천미트", "price_per_kg": 24300, "weight_kg": 10.3,
             "gender": "거세", "grade": "2등급A", "cut": "목심",
             "url": "https://example.com"},
        ]
        await cmd_recommend(update, context)

    mock_prices.assert_called_once_with(10.0)
    update.message.reply_text.assert_called_once()


@pytest.mark.asyncio
async def test_stop_command():
    from bot import cmd_stop
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    with patch("bot.db.set_alert_active") as mock_set:
        await cmd_stop(update, context)
        mock_set.assert_called_once_with(False)
