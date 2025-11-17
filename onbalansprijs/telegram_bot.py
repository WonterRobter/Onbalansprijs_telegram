import logging
import time

from onbalansprijs.logging_helpers import session
from onbalansprijs.elia_api import haal_onbalansprijs_op

def stuur_telegram_bericht(token: str, bericht: str, chat_id: str, retries: int = 3):
    """Stuur een bericht naar Telegram met retries en exponentiële backoff."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"text": bericht, "chat_id": chat_id}
    backoff = 2

    for attempt in range(retries):
        try:
            logging.debug(f"Verstuur bericht naar chat_id {chat_id}. Bericht: {bericht}")
            response = session.post(url, json=payload, timeout=10)
            response.raise_for_status()
            logging.info(f"✅ Bericht succesvol verzonden naar {chat_id}.")
            return True
        except Exception as e:
            logging.error(f"❌ Fout bij verzenden naar {chat_id}: {e}")
            if attempt < retries - 1:
                time.sleep(backoff)
                backoff *= 2
    return False

def stuur_rebootbericht(token: str, chat_ids: list[str], prijs: float, timestamp_obj):
    """Stuur een rebootbericht met de eerste prijsinformatie naar alle chat IDs."""
    prijs_rond = round(prijs)
    tijd_str = f"🕒 Tijd: {timestamp_obj.hour}:{timestamp_obj.minute:02}"
    bericht = f'🔄 Server herstart!: {prijs_rond} €/MWh\n{tijd_str}'
    for chat_id in chat_ids:
        stuur_telegram_bericht(token, bericht, chat_id)

def verwerk_telegram_bericht(token: str, api_url: str, bericht: str, chat_id: str):
    """Verwerk inkomend Telegram-bericht en reageer indien nodig."""
    logging.debug(f"Inkomend bericht: {bericht} van chat_id {chat_id}")
    if bericht.strip() == "/price":
        prijs, timestamp_obj = haal_onbalansprijs_op(api_url)
        if prijs is not None and timestamp_obj is not None:
            prijs_rond = round(prijs)
            tijd_str = f"🕒 Tijd: {timestamp_obj.hour}:{timestamp_obj.minute:02}"
            reactie = f"Huidige onbalansprijs: {prijs_rond} €/MWh\n{tijd_str}"
            stuur_telegram_bericht(token, reactie, chat_id)
        else:
            stuur_telegram_bericht(token, "⚠️ Fout bij ophalen van de prijsinformatie.", chat_id)

def monitor_telegram(token: str, chat_ids_allowlist: list[str] | None = None):
    """Controleer regelmatig op inkomende berichten en reageer daarop.
       Let op: dit leest updates en verwerkt enkel tekstberichten.
    """
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    last_update_id = None

    while True:
        params = {'offset': last_update_id}
        try:
            response = session.get(url, params=params, timeout=10)
            response.raise_for_status()
            updates = response.json().get('result', [])

            for update in updates:
                message = update.get('message', {})
                chat_id = str(message.get('chat', {}).get('id'))
                tekst = message.get('text', '').strip()
                last_update_id = update['update_id'] + 1

                # Allowlist check (optioneel)
                if chat_ids_allowlist and chat_id not in chat_ids_allowlist:
                    continue

                if chat_id and tekst:
                    yield chat_id, tekst  # laat scheduler beslissen wat ermee te doen

            time.sleep(1)
        except Exception as e:
            logging.error(f"❌ Fout bij ophalen van Telegram updates: {e}")
            time.sleep(5)
