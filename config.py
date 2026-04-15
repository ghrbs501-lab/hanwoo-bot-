import os

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "hanwoo.db")

TARGET_CUT = "목심"
TARGET_GRADE = "2등급"

LOG_PATH = os.path.join(os.path.dirname(__file__), "logs", "hanwoo.log")
