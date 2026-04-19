import pytest
from unittest.mock import patch, MagicMock
from alert import check_and_notify, format_alert_message

SAMPLE_ITEM = {
    "site": "금천미트",
    "grade": "2등급A",
    "cut": "목심",
    "gender": "거세",
    "price_per_kg": 24300,
    "weight_kg": 10.3,
    "url": "https://www.ekcm.co.kr/pd/productDetail?goodsNo=12345",
}


def test_format_alert_message():
    msg = format_alert_message(SAMPLE_ITEM, target_price=25000)
    assert "금천미트" in msg
    assert "24,300" in msg
    assert "25,000" in msg
    assert "https://www.ekcm.co.kr" in msg


def test_check_and_notify_sends_when_below_target():
    config_row = {"target_price": 25000, "active": 1, "cut": "목심", "grade": "2등급"}
    with patch("alert.send_telegram") as mock_send:
        check_and_notify([SAMPLE_ITEM], config_row)
        assert mock_send.called


def test_check_and_notify_no_send_when_above_target():
    config_row = {"target_price": 24000, "active": 1, "cut": "목심", "grade": "2등급"}
    with patch("alert.send_telegram") as mock_send:
        check_and_notify([SAMPLE_ITEM], config_row)
        assert not mock_send.called


def test_check_and_notify_skips_when_inactive():
    config_row = {"target_price": 25000, "active": 0, "cut": "목심", "grade": "2등급"}
    with patch("alert.send_telegram") as mock_send:
        check_and_notify([SAMPLE_ITEM], config_row)
        assert not mock_send.called


def test_check_and_notify_skips_when_config_none():
    with patch("alert.send_telegram") as mock_send:
        check_and_notify([SAMPLE_ITEM], None)
        assert not mock_send.called


def test_check_and_notify_sends_multiple_below_target():
    items = [
        {**SAMPLE_ITEM, "price_per_kg": 23000},
        {**SAMPLE_ITEM, "price_per_kg": 24500, "site": "미트박스"},
        {**SAMPLE_ITEM, "price_per_kg": 26000, "site": "탑미트"},
    ]
    config_row = {"target_price": 25000, "active": 1, "cut": "목심", "grade": "2등급"}
    with patch("alert.send_telegram") as mock_send:
        check_and_notify(items, config_row)
        assert mock_send.call_count == 2
