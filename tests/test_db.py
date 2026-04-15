import os
import tempfile
import pytest
from db import init_db, save_prices, get_latest_prices, get_alert_config, set_alert_config, get_prices_above_weight

@pytest.fixture
def tmp_db(monkeypatch, tmp_path):
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr("db.DB_PATH", db_file)
    init_db()
    return db_file

def test_init_db_creates_tables(tmp_db):
    import sqlite3
    conn = sqlite3.connect(tmp_db)
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    table_names = [t[0] for t in tables]
    assert "prices" in table_names
    assert "alert_config" in table_names
    conn.close()

def test_save_and_get_prices(tmp_db):
    items = [
        {
            "site": "금천미트",
            "grade": "2등급",
            "cut": "목심",
            "gender": "암소",
            "price_per_kg": 18500,
            "weight_kg": 10.2,
            "url": "https://example.com/1",
            "crawled_at": "2026-04-14 09:30:00",
        }
    ]
    save_prices(items)
    results = get_latest_prices()
    assert len(results) == 1
    assert results[0]["site"] == "금천미트"
    assert results[0]["price_per_kg"] == 18500

def test_alert_config_default_inactive(tmp_db):
    config = get_alert_config()
    assert config is None or config["active"] == 0

def test_set_and_get_alert_config(tmp_db):
    set_alert_config(cut="목심", grade="2등급", target_price=18000, active=True)
    config = get_alert_config()
    assert config["target_price"] == 18000
    assert config["active"] == 1

def test_get_prices_above_weight(tmp_db):
    items = [
        {
            "site": "금천미트", "grade": "2등급", "cut": "목심", "gender": "암소",
            "price_per_kg": 18500, "weight_kg": 10.2,
            "url": "https://example.com/1", "crawled_at": "2026-04-14 09:30:00",
        },
        {
            "site": "미트박스", "grade": "2등급", "cut": "목심", "gender": "거세",
            "price_per_kg": 17000, "weight_kg": 55.0,
            "url": "https://example.com/2", "crawled_at": "2026-04-14 09:30:00",
        },
    ]
    save_prices(items)
    results = get_prices_above_weight(50.0)
    assert len(results) == 1
    assert results[0]["site"] == "미트박스"
    assert results[0]["weight_kg"] == 55.0

def test_set_alert_active(tmp_db):
    set_alert_config(cut="목심", grade="2등급", target_price=18000, active=True)
    from db import set_alert_active, get_alert_config
    set_alert_active(False)
    config = get_alert_config()
    assert config["active"] == 0
    set_alert_active(True)
    config = get_alert_config()
    assert config["active"] == 1
