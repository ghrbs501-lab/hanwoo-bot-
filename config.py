import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
KAMIS_API_KEY = os.environ.get("KAMIS_API_KEY", "")

DATABASE_URL = os.environ.get("DB_CONN_URL", "")

DB_HOST     = os.environ.get("DB_HOST", "")
DB_PORT     = int(os.environ.get("DB_PORT", "5432"))
DB_NAME     = os.environ.get("DB_NAME", "postgres")
DB_USER     = os.environ.get("DB_USER", "")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")

TARGET_CUT = "목심"
TARGET_GRADE = "2등급"

LOG_PATH = os.path.join(os.path.dirname(__file__), "logs", "hanwoo.log")
