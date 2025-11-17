import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_IDS = os.getenv("TELEGRAM_CHAT_IDS", "")
TELEGRAM_CHAT_IDS = [id.strip() for id in TELEGRAM_CHAT_IDS.split(",") if id.strip()]
ELIA_API_URL = os.getenv('ELIA_API_URL')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Basisvalidaties (optioneel, maar handig)
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN ontbreekt in omgeving of .env")
if not ELIA_API_URL:
    raise ValueError("ELIA_API_URL ontbreekt in omgeving of .env")
if not TELEGRAM_CHAT_IDS:
    raise ValueError("TELEGRAM_CHAT_IDS ontbreekt of is leeg in omgeving of .env")
