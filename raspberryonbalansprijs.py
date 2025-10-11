import requests
import time
import logging
from datetime import datetime
import pytz
import threading
import os
from dotenv import load_dotenv
load_dotenv()

# Logging instellen - logniveau aangepast naar INFO
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Telegram configuratie
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_IDS = os.getenv("TELEGRAM_CHAT_IDS", "")
TELEGRAM_CHAT_IDS = [id.strip() for id in TELEGRAM_CHAT_IDS.split(",") if id.strip()]

# Elia API URL
ELIA_API_URL = os.getenv('ELIA_API_URL')

# Belgische tijdzone
BELGIUM_TZ = pytz.timezone('Europe/Brussels')

# Maak een requests sessie aan
session = requests.Session()

def stuur_telegram_bericht(bericht, chat_id, retries=3):
    """Stuur een bericht naar Telegram en probeer opnieuw bij een fout."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"text": bericht, "chat_id": chat_id}

    backoff = 2
    for attempt in range(retries):
        try:
            logging.debug(f"Verstuur bericht naar chat_id {chat_id}. Bericht: {bericht}")
            response = session.post(url, json=payload, timeout=10)
            response.raise_for_status()  # Controleer of de API-call succesvol was
            logging.info(f"✅ Bericht succesvol verzonden naar {chat_id}.")
            break  # Als succesvol, stop dan met verdere pogingen
        except requests.exceptions.RequestException as e:
            logging.error(f"❌ Fout bij verzenden naar {chat_id}: {e}")
            if attempt < retries - 1:
                time.sleep(backoff)
                backoff *= 2  # Exponentiële backoff

def doe_http_aanroep(url, retries=3, timeout=10):
    """Voer een HTTP-aanroep uit en haal de JSON-gegevens op."""
    logging.debug(f"Voer HTTP-aanroep uit naar {url}")
    for attempt in range(retries):
        try:
            response = session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            logging.error(f"❌ HTTP fout: {http_err}")
            if attempt < retries - 1:
                time.sleep(5)
    return None

def haal_onbalansprijs_op():
    """Haalt de laatste onbalansprijs op en retourneert deze samen met de timestamp."""
    data = doe_http_aanroep(ELIA_API_URL)
    if not data or 'results' not in data or not isinstance(data['results'], list) or not data['results']:
        logging.warning("⚠️ Geen geldige data ontvangen.")
        return None, None
    
    laatste_data = data['results'][0]
    prijs = laatste_data.get('imbalanceprice')
    timestamp = laatste_data.get('datetime')
    
    if prijs is None:
        logging.warning("⚠️ Geen prijsinformatie beschikbaar.")
        return None, None
    
    timestamp_obj = datetime.fromisoformat(timestamp).astimezone(BELGIUM_TZ)
    return prijs, timestamp_obj

def beheer_prijsstatus(prijs, laatste_prijs, status, timestamp_obj):
    prijs = round(prijs)
    tijd_str = f"🕒 Tijd: {timestamp_obj.hour}:{timestamp_obj.minute:02}"

    if prijs != laatste_prijs:
        logging.info(f"📊 Onbalansprijs veranderd: {prijs} €\MWh ({tijd_str})")

        # Prioriteit 1: EXTREEM laag (< -500)
        if prijs < -500 and not status.get('extreem_laag', False):
            for chat_id in TELEGRAM_CHAT_IDS:
                stuur_telegram_bericht(f'🧊 EXTREEM lage onbalansprijs: {prijs} €\MWh\n{tijd_str}', chat_id)
            status['extreem_laag'] = True
            status['zeer_laag'] = True
            status['onder_min_50'] = True
            status['onder_0'] = True
            status['onder_50'] = True
            status['zeer_hoog'] = False  # Reset hoog als prijs extreem laag is
            return prijs, status

        # Prioriteit 2: ZÉÉR laag (< -150)
        if prijs < -150 and not status.get('zeer_laag', False):
            for chat_id in TELEGRAM_CHAT_IDS:
                stuur_telegram_bericht(f'❄️ ZÉÉR lage onbalansprijs: {prijs} €\MWh\n{tijd_str}', chat_id)
            status['zeer_laag'] = True
            status['onder_min_50'] = True
            status['onder_0'] = True
            status['onder_50'] = True
            status['zeer_hoog'] = False
            return prijs, status

        # Prioriteit 3: ZÉÉR HOOG (> 400)
        if prijs > 400 and not status.get('zeer_hoog', False):
            for chat_id in TELEGRAM_CHAT_IDS:
                stuur_telegram_bericht(f'🚨 ZÉÉR HOGE onbalansprijs: {prijs} €\MWh\n{tijd_str}', chat_id)
            status['zeer_hoog'] = True
            # Reset lage flags omdat prijs nu hoog is
            status['extreem_laag'] = False
            status['zeer_laag'] = False
            status['onder_min_50'] = False
            status['onder_0'] = False
            status['onder_50'] = False
            return prijs, status

        # Prioriteit 4: onder -50
        if prijs < -50 and not status.get('onder_min_50', False):
            for chat_id in TELEGRAM_CHAT_IDS:
                stuur_telegram_bericht(f'🌟 Onbalansprijs onder -50 : {prijs} €\MWh\n{tijd_str}', chat_id)
            status['onder_min_50'] = True
            status['onder_0'] = True
            status['onder_50'] = True
            status['zeer_hoog'] = False
            return prijs, status

        # Prioriteit 5: onder 0
        if prijs < 0 and not status.get('onder_0', False):
            for chat_id in TELEGRAM_CHAT_IDS:
                stuur_telegram_bericht(f'✅ Onbalansprijs onder 0 : {prijs} €\MWh\n{tijd_str}', chat_id)
            status['onder_0'] = True
            status['onder_50'] = True
            status['zeer_hoog'] = False
            return prijs, status

        # Prioriteit 6: onder 50 (maar boven 0)
        if 0 < prijs < 50 and not status.get('onder_50', False):
            for chat_id in TELEGRAM_CHAT_IDS:
                stuur_telegram_bericht(f'⚠️ Onbalansprijs onder 50 : {prijs} €\MWh\n{tijd_str}', chat_id)
            status['onder_50'] = True
            status['zeer_hoog'] = False
            return prijs, status

        # Herstelmeldingen (hoogste prioriteit eerst)

        # Herstel onder 50 en lager
        if prijs >= 50 and status.get('onder_50', False):
            for chat_id in TELEGRAM_CHAT_IDS:
                stuur_telegram_bericht(f'🚨 Onbalansprijs boven 50 : {prijs} €\MWh\n{tijd_str}', chat_id)
            status['onder_50'] = False
            status['onder_0'] = False
            status['onder_min_50'] = False

        elif prijs >= 0 and status.get('onder_0', False):
            for chat_id in TELEGRAM_CHAT_IDS:
                stuur_telegram_bericht(f'⚠️ Onbalansprijs boven 0 : {prijs} €\MWh\n{tijd_str}', chat_id)
            status['onder_0'] = False
            status['onder_min_50'] = False

        elif prijs >= -50 and status.get('onder_min_50', False):
            for chat_id in TELEGRAM_CHAT_IDS:
                stuur_telegram_bericht(f'☑️ Onbalansprijs boven -50 : {prijs} €\MWh\n{tijd_str}', chat_id)
            status['onder_min_50'] = False

    return prijs, status

def stuur_rebootbericht(prijs, timestamp_obj):
    """Stuur een rebootbericht met de eerste prijsinformatie naar beide gebruikers."""
    prijs = round(prijs)
    tijd_str = f"🕒 Tijd: {timestamp_obj.hour}:{timestamp_obj.minute:02}"
    bericht = f'🔄 Server herstart!: {prijs} €\MWh\n{tijd_str}'
    
    # Verstuur het bericht naar elke chat ID
    for chat_id in TELEGRAM_CHAT_IDS:
        stuur_telegram_bericht(bericht, chat_id)

def verwerk_telegram_bericht(bericht, chat_id):
    """Verwerk inkomend Telegram-bericht en reageer indien nodig."""
    logging.debug(f"Inkomend bericht: {bericht} van chat_id {chat_id}")
    if bericht.strip() == "/price":
        prijs, timestamp_obj = haal_onbalansprijs_op()
        if prijs is not None and timestamp_obj is not None:
            prijs = round(prijs)
            tijd_str = f"🕒 Tijd: {timestamp_obj.hour}:{timestamp_obj.minute:02}"
            reactie = f"Huidige onbalansprijs: {prijs} €\MWh\n{tijd_str}"
            stuur_telegram_bericht(reactie, chat_id)  # Stuur bericht naar degene die het commando uitvoert
        else:
            stuur_telegram_bericht("⚠️ Fout bij ophalen van de prijsinformatie.", chat_id)

def monitor_telegram():
    """Controleer regelmatig op inkomende berichten en reageer daarop."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    
    last_update_id = None
    while True:
        params = {'offset': last_update_id}
        try:
            response = session.get(url, params=params, timeout=10)
            response.raise_for_status()
            updates = response.json().get('result', [])
            
            for update in updates:
                message = update.get('message', {})
                chat_id = message.get('chat', {}).get('id')
                tekst = message.get('text', '').strip()
                last_update_id = update['update_id'] + 1  # Update de laatste ID om nieuwe berichten te krijgen
                
                if chat_id and tekst:
                    verwerk_telegram_bericht(tekst, chat_id)
            
            time.sleep(1)
        except requests.exceptions.RequestException as e:
            logging.error(f"❌ Fout bij ophalen van Telegram updates: {e}")
            time.sleep(5)

def prijscontrole():
    """Controleer regelmatig de prijs en stuur meldingen."""
    laatste_prijs = None
    status = {
        'onder_50': False,
        'onder_0': False,
        'onder_min_50': False,
        'zeer_hoog': False,          # > 300
        'zeer_laag': False,          # < -150
        'extreem_laag': False        # < -500
    }

    # Stuur reboot bericht bij opstart
    prijs, timestamp_obj = haal_onbalansprijs_op()
    if prijs is not None and timestamp_obj is not None:
        stuur_rebootbericht(prijs, timestamp_obj)

    # Hoofdloop die elke 15 seconden de prijs controleert
    while True:
        try:
            prijs, timestamp_obj = haal_onbalansprijs_op()
            
            if prijs is not None and timestamp_obj is not None:
                laatste_prijs, status = beheer_prijsstatus(prijs, laatste_prijs, status, timestamp_obj)
            
            time.sleep(15)
        except Exception as e:
            logging.error(f"❌ Onverwachte fout: {e}")
            time.sleep(60)

def main():
    """Hoofdprogramma dat beide processen tegelijkertijd uitvoert."""
    # Start de prijscontrole in een aparte thread
    prijs_thread = threading.Thread(target=prijscontrole)
    prijs_thread.daemon = True  # Zorg ervoor dat de thread stopt wanneer het hoofdprogramma stopt
    prijs_thread.start()

    # Start de Telegram monitoring in de hoofdthread
    monitor_telegram()

if __name__ == "__main__":
    main()