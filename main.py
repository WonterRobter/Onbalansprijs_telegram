import logging
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_IDS, ELIA_API_URL, LOG_LEVEL
from onbalansprijs import start_threads   # alles netjes via __init__.py
from onbalansprijs.logging_helpers import setup_logging

def main():
    setup_logging(LOG_LEVEL)
    logging.info("Onbalansprijs Telegram bot gestart")
    start_threads(ELIA_API_URL, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_IDS, interval_sec=15)

if __name__ == "__main__":
    main()
