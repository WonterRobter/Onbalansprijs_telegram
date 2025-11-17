import logging
from datetime import datetime
import pytz

from onbalansprijs.logging_helpers import session

def doe_http_aanroep(url, retries=3, timeout=10):
    """Voer een HTTP-aanroep uit en haal de JSON-gegevens op met retries."""
    for attempt in range(retries):
        try:
            resp = session.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logging.error(f"❌ HTTP fout: {e}")
    return None

def haal_onbalansprijs_op(api_url: str, tz_name: str = 'Europe/Brussels'):
    """Haalt de laatste onbalansprijs op en retourneert (prijs, timestamp_obj)."""
    data = doe_http_aanroep(api_url)
    if not data or 'results' not in data or not isinstance(data['results'], list) or not data['results']:
        logging.warning("⚠️ Geen geldige data ontvangen.")
        return None, None

    laatste_data = data['results'][0]
    prijs = laatste_data.get('imbalanceprice')
    timestamp = laatste_data.get('datetime')

    if prijs is None or timestamp is None:
        logging.warning("⚠️ Geen prijs- of tijdsinformatie beschikbaar.")
        return None, None

    tz = pytz.timezone(tz_name)
    timestamp_obj = datetime.fromisoformat(timestamp).astimezone(tz)
    return prijs, timestamp_obj
