import logging
import time
import threading

from onbalansprijs.elia_api import haal_onbalansprijs_op
from onbalansprijs.prijs_logic import beheer_prijsstatus
from onbalansprijs.telegram_bot import monitor_telegram, verwerk_telegram_bericht, stuur_rebootbericht

def prijscontrole(api_url: str, token: str, chat_ids: list[str], interval_sec: int = 15):
    """Controleer regelmatig de prijs en stuur meldingen."""
    laatste_prijs = None
    status = {
        'onder_50': False,
        'onder_0': False,
        'onder_min_50': False,
        'zeer_hoog': False,          # > 400
        'zeer_laag': False,          # < -150
        'extreem_laag': False        # < -500
    }

    # Stuur reboot bericht bij opstart
    prijs, timestamp_obj = haal_onbalansprijs_op(api_url)
    if prijs is not None and timestamp_obj is not None:
        stuur_rebootbericht(token, chat_ids, prijs, timestamp_obj)

    # Hoofdloop
    while True:
        try:
            prijs, timestamp_obj = haal_onbalansprijs_op(api_url)
            if prijs is not None and timestamp_obj is not None:
                laatste_prijs, status = beheer_prijsstatus(
                    prijs, laatste_prijs, status, timestamp_obj, token, chat_ids
                )
            time.sleep(interval_sec)
        except Exception as e:
            logging.error(f"❌ Onverwachte fout in prijscontrole: {e}")
            time.sleep(60)

def start_threads(api_url: str, token: str, chat_ids: list[str], interval_sec: int = 15):
    """Start de prijscontrole in een thread en run de Telegram monitoring in de main-loop."""
    prijs_thread = threading.Thread(target=prijscontrole, args=(api_url, token, chat_ids, interval_sec))
    prijs_thread.daemon = True  # Thread stopt wanneer hoofdprogramma stopt
    prijs_thread.start()

    # Telegram monitoring in deze thread (blokkerend), en commando's verwerken
    for chat_id, tekst in monitor_telegram(token, chat_ids_allowlist=chat_ids):
        verwerk_telegram_bericht(token, api_url, tekst, chat_id)
