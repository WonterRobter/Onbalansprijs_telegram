import requests
import time
from datetime import date
import logging
import threading
import os
import pytz
from datetime import datetime, timedelta
from dotenv import load_dotenv

import matplotlib
matplotlib.use('Agg') # Zorgt dat hij kan tekenen zonder beeldscherm
import matplotlib.pyplot as plt
import io # Nodig om plaatjes in het geheugen op te slaan
import matplotlib.dates as mdates # Voor mooie tijd-as

# =============================================================================
# 1. CONFIGURATIE & INSTELLINGEN
# =============================================================================

# Laad variabelen uit het .env bestand
load_dotenv()

# Logging instellen
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Telegram instellingen ophalen
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_IDS_RAW = os.getenv("TELEGRAM_CHAT_IDS", "")

# Zorg dat de chat ID's in een nette lijst komen (gescheiden door komma's)
TELEGRAM_CHAT_IDS = [id.strip() for id in TELEGRAM_CHAT_IDS_RAW.split(",") if id.strip()]

# Elia API instellingen
ELIA_API_URL = os.getenv('ELIA_API_URL')

# Tijdzone instellingen
BELGIUM_TZ = pytz.timezone('Europe/Brussels')

# Sessie instellingen
session = requests.Session()

# DATA OPSLAG
history_prices = [] # De Y-as (Prijs)
history_times = []  # De X-as (Tijd)
laatste_datum = datetime.now(BELGIUM_TZ).date()

# Variabele om te voorkomen dat we om 23:59 elke seconde een rapport sturen
dagrapport_verstuurd = False 

# =============================================================================
# 2. HULPFUNCTIES (TELEGRAM, API & GENERATIE)
# =============================================================================

def stuur_telegram_bericht(bericht, chat_id, retries=3):
    """
    Stuurt een tekstbericht naar een specifieke Telegram-gebruiker.
    Gebruikt HTML-opmaak (dikgedrukt/cursief).
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # We voegen 'parse_mode': 'HTML' toe zodat Telegram de opmaak begrijpt
    payload = {"text": bericht, "chat_id": chat_id, "parse_mode": "HTML"}
    backoff = 2
    
    for attempt in range(retries):
        try:
            # Debug log (zonder HTML tags voor leesbaarheid in console)
            logging.debug(f"Poging {attempt+1}: Verstuur bericht naar {chat_id}")
            response = session.post(url, json=payload, timeout=10)
            response.raise_for_status() # Geeft een fout als de statuscode niet 200 is
            
            logging.info(f"✅ Bericht verzonden naar {chat_id}")
            break
        except requests.exceptions.RequestException as e:
            logging.error(f"❌ Fout bij verzenden bericht (poging {attempt+1}): {e}")
            if attempt < retries - 1:
                time.sleep(backoff)
                backoff *= 2 # Wacht steeds iets langer (2s, 4s, 8s...)

def stuur_telegram_foto(photo_buffer, chat_id):
    """ Stuurt een afbeelding naar Telegram """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    
    # We sturen de buffer als een bestand
    files = {'photo': ('grafiek.png', photo_buffer, 'image/png')}
    data = {'chat_id': chat_id}
    
    try:
        response = session.post(url, data=data, files=files, timeout=20)
        response.raise_for_status()
        logging.info(f"📸 Grafiek verzonden naar {chat_id}")
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Fout bij sturen foto: {e}")

def doe_http_aanroep(url, retries=3, timeout=10):
    """
    Haalt data op van een URL (Elia API).
    Probeert het opnieuw als de server even niet reageert.
    """
    for attempt in range(retries):
        try:
            response = session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"❌ API Fout (poging {attempt+1}): {e}")
            if attempt < retries - 1:
                time.sleep(5)
    return None

def genereer_grafiek_afbeelding():
    """
    Maakt de grafiek en geeft de buffer terug.
    FILTERT de data: toont alleen kwartierwaarden (contractprijzen).
    """
    if len(history_prices) < 2:
        return None

    try:
        plot_times = []
        plot_prices = []
        
        for t, p in zip(history_times, history_prices):
            # Settlement check: is dit het einde van een kwartier?
            if t.minute % 15 == 14 and t.second >= 30:
                plot_times.append(t)
                plot_prices.append(p)
        if len(plot_prices) < 2:
            return None
        
        plt.figure(figsize=(10, 5))
        
        # plotten nu de GEFILTERDE lijsten
        plt.plot(plot_times, plot_prices, color='blue', linewidth=2, marker='o', markersize=4)
        
        plt.title(f"Settlement Prijzen ({datetime.now(BELGIUM_TZ).strftime('%d-%m-%Y')})")
        plt.ylabel("Prijs (€/MWh)")
        plt.grid(True, linestyle='--', alpha=0.7)
        
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M', tz=BELGIUM_TZ))
        plt.gcf().autofmt_xdate()
        plt.axhline(0, color='red', linewidth=1, linestyle='-')

        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close()
        buf.seek(0)
        return buf
    except Exception as e:
        logging.error(f"Fout in grafiek generatie: {e}")
        return None

def genereer_dag_samenvatting():
    """
    Maakt de tekst voor het dagoverzicht.
    """
    if not history_prices:
        return "📉 Nog geen metingen verzameld vandaag."
    
    laagste = round(min(history_prices))
    hoogste = round(max(history_prices))
    gemiddelde = round(sum(history_prices) / len(history_prices))
    
    return (
        f"🏁 <b>📊 Overzicht Vandaag</b>\n\n"
        f"📉 Laagste: <b>{laagste} €\MWh</b>\n"
        f"📈 Hoogste: <b>{hoogste} €\MWh</b>\n"
        f"⚖️ Gemiddeld: <b>{gemiddelde} €\MWh</b>\n"
        f"⏱️ Aantal metingen: {len(history_prices)}"
    )

# =============================================================================
# 3. KERNLOGICA
# =============================================================================

def haal_onbalansprijs_op():
    data = doe_http_aanroep(ELIA_API_URL)
    if not data or 'results' not in data or not data['results']:
        logging.warning("⚠️ Geen geldige data ontvangen van Elia.")
        return None, None
    
    laatste_data = data['results'][0]
    prijs = laatste_data.get('imbalanceprice')
    timestamp = laatste_data.get('datetime')
    
    if prijs is None: 
        return None, None
    
    timestamp_obj = datetime.fromisoformat(timestamp).astimezone(BELGIUM_TZ)
    return prijs, timestamp_obj

def beheer_prijsstatus(prijs, laatste_prijs, status, timestamp_obj):
    """
    Vergelijkt de nieuwe prijs met de grenswaardes en bepaalt of er een melding moet komen.
    Opmaak: Titel VET, Prijs NORMAAL, Tijd SCHUIN.
    """
    prijs = round(prijs) # Rond af op hele euro's
    tijd_str = f"{timestamp_obj.hour}:{timestamp_obj.minute:02}" # Tijd zonder tekst voor in bericht

    # Alleen loggen in de console als de prijs daadwerkelijk verandert
    if prijs != laatste_prijs:
        logging.info(f"📊 Nieuwe prijs ontvangen: {prijs} €\\MWh ({tijd_str})")

        # Hulpfunctie voor de opmaak
        def maak_bericht(titel, icoon):
            # \n betekent: ga naar de volgende regel
            return f"{icoon} <b>{titel}:</b> {prijs} €\\MWh\n <i>{tijd_str}</i>"

        # --- CONTROLE: EXTREME PRIJZEN ---

        # 1. Extreem laag (< -500)
        if prijs < -500 and not status.get('extreem_laag'):
            for chat_id in TELEGRAM_CHAT_IDS:
                stuur_telegram_bericht(maak_bericht("EXTREEM LAGE PRIJS", "🧊"), chat_id)
            status.update({
                'extreem_laag': True, 
                'zeer_laag': True, 
                'onder_min_50': True, 
                'onder_0': True, 
                'onder_50': True, 
                'zeer_hoog': False })
            return prijs, status

        # 2. Zeer laag (< -150)
        if prijs < -150 and not status.get('zeer_laag'):
            for chat_id in TELEGRAM_CHAT_IDS:
                stuur_telegram_bericht(maak_bericht("ZÉÉR LAGE PRIJS", "❄️"), chat_id)
            status.update({
                'zeer_laag': True, 
                'onder_min_50': True, 
                'onder_0': True, 
                'onder_50': True, 
                'zeer_hoog': False })
            return prijs, status

        # 3. Zeer hoog (> 400)
        if prijs > 400 and not status.get('zeer_hoog'):
            for chat_id in TELEGRAM_CHAT_IDS:
                stuur_telegram_bericht(maak_bericht("ZÉÉR HOGE PRIJS", "🚨"), chat_id)
            status.update({
                'zeer_hoog': True, 
                'extreem_laag': False, 
                'zeer_laag': False, 
                'onder_min_50': False, 
                'onder_0': False, 
                'onder_50': False})
            return prijs, status

        # 4. Onder -50
        if prijs < -50 and not status.get('onder_min_50'):
            for chat_id in TELEGRAM_CHAT_IDS:
                stuur_telegram_bericht(maak_bericht("Prijs onder -50", "🌟"), chat_id)
            status.update({
                'onder_min_50': True, 
                'onder_0': True, 
                'onder_50': True, 
                'zeer_hoog': False })
            return prijs, status

        # 5. Onder 0 (Negatief)
        if prijs < 0 and not status.get('onder_0'):
            for chat_id in TELEGRAM_CHAT_IDS:
                stuur_telegram_bericht(maak_bericht("Prijs onder 0", "✅"), chat_id)
            status.update({
                'onder_0': True, 
                'onder_50': True, 
                'zeer_hoog': False })
            return prijs, status

        # 6. Onder 50 (Goedkoop)
        if 0 < prijs < 50 and not status.get('onder_50'):
            for chat_id in TELEGRAM_CHAT_IDS:
                stuur_telegram_bericht(maak_bericht("Prijs onder 50", "⚠️"), chat_id)
            status.update({
                'onder_50': True, 
                'zeer_hoog': False })
            return prijs, status

        # --- HERSTEL ---
        if prijs >= 60 and status.get('onder_50'):
            for chat_id in TELEGRAM_CHAT_IDS:
                stuur_telegram_bericht(maak_bericht("Prijs weer boven 50", "📈"), chat_id)
            status.update({
                'onder_50': False, 
                'onder_0': False, 
                'onder_min_50': False })
        
        # Herstel: Boven 0
        elif prijs >= 0 and status.get('onder_0'):
            for chat_id in TELEGRAM_CHAT_IDS:
                stuur_telegram_bericht(maak_bericht("Prijs weer positief", "⚠️"), chat_id)
            status.update({
                'onder_0': False, 
                'onder_min_50': False })

        # Herstel: Boven -50
        elif prijs >= -50 and status.get('onder_min_50'):
            for chat_id in TELEGRAM_CHAT_IDS:
                stuur_telegram_bericht(maak_bericht("Prijs weer boven -50", "☑️"), chat_id)
            status.update({'onder_min_50': False})

    return prijs, status

# =============================================================================
# 4. HOOFDPROCESSEN
# =============================================================================

def monitor_telegram():
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    last_update_id = None
    logging.info("🤖 Telegram monitor gestart...")
    
    while True:
        params = {'offset': last_update_id, 'timeout': 30}
        try:
            response = session.get(url, params=params, timeout=35)
            response.raise_for_status()
            updates = response.json().get('result', [])
            
            for update in updates:
                last_update_id = update['update_id'] + 1
                message = update.get('message', {})
                tekst = message.get('text', '').strip()
                chat_id = message.get('chat', {}).get('id')
                
                if chat_id:
                    # 1. Commando /price
                    if tekst == "/price":
                        logging.info(f"📩 Commando /price ontvangen van {chat_id}")
                        prijs, timestamp_obj = haal_onbalansprijs_op()
                        if prijs is not None:
                            tijd_str = f"{timestamp_obj.hour}:{timestamp_obj.minute:02}"
                            stuur_telegram_bericht(f"ℹ️ <b>Huidige prijs:</b> {round(prijs)} €\\MWh\n <i>{tijd_str}</i>", chat_id)
                        else:
                            stuur_telegram_bericht("⚠️ Kon prijs niet ophalen.", chat_id)

                    # 2. Commando /vandaag
                    elif tekst == "/vandaag":
                        logging.info(f"📩 Commando /vandaag ontvangen van {chat_id}")
                        stuur_telegram_bericht(genereer_dag_samenvatting(), chat_id)
                    
                    # 3. Commando /grafiek
                    elif tekst == "/grafiek":
                        logging.info(f"📩 Commando /grafiek ontvangen van {chat_id}")
                        stuur_telegram_bericht("🎨 Grafiek wordt gemaakt...", chat_id)
                        buf = genereer_grafiek_afbeelding()
                        if buf:
                            stuur_telegram_foto(buf, chat_id)
                            buf.close()
                        else:
                            stuur_telegram_bericht("📉 Te weinig data voor grafiek.", chat_id)
            
            time.sleep(1)
        except Exception as e:
            logging.error(f"Telegram fout: {e}")
            time.sleep(5)

def prijscontrole_loop():
    """
    Checkt elke 15 seconden de prijs en werkt de status bij.
    Slaat ook de prijzen op voor de statistieken.
    """
    # We moeten aangeven dat we de globale variabelen willen gebruiken
    global history_prices, history_times, laatste_datum, dagrapport_verstuurd
    laatste_prijs = None
    status = {'onder_50': False, 'onder_0': False, 'onder_min_50': False, 'zeer_laag': False, 'extreem_laag': False, 'zeer_hoog': False}

    logging.info("⚡ Prijscontrole gestart...")
    
    # Startup bericht
    prijs, timestamp_obj = haal_onbalansprijs_op()
    if prijs is not None:
        tijd_str = f"{timestamp_obj.hour}:{timestamp_obj.minute:02}"
        for chat_id in TELEGRAM_CHAT_IDS:
            stuur_telegram_bericht(f'🔄 <b>Server herstart</b> {round(prijs)} €\\MWh\n<i>{tijd_str}</i>', chat_id)

    # Oneindige loop
    while True:
        try:
            nu_belgie = datetime.now(BELGIUM_TZ)
            prijs, timestamp_obj = haal_onbalansprijs_op()
            
            if prijs is not None:
                # 1. Resetten bij nieuwe dag
                vandaag = nu_belgie.date()
                if vandaag != laatste_datum:
                    history_prices = []
                    history_times = []
                    laatste_datum = vandaag
                    dagrapport_verstuurd = False # Reset vlag voor de nieuwe dag
                    logging.info("📅 Nieuwe dag: data gereset.")

                # 2. Data toevoegen
                history_prices.append(prijs)
                history_times.append(nu_belgie)

                # 3. Status updates (alarmen)
                if timestamp_obj:
                    laatste_prijs, status = beheer_prijsstatus(prijs, laatste_prijs, status, timestamp_obj)

            # 4. --- AUTOMATISCHE DAGAFSLUITING OM 23:59 ---
            # We checken of het 23:59 is EN of we het rapport nog niet gestuurd hebben
            if nu_belgie.hour == 23 and nu_belgie.minute == 59 and not dagrapport_verstuurd:
                logging.info("🕛 Tijd voor dagafsluiting! Rapport versturen...")
                
                # Samenvatting maken
                tekst = genereer_dag_samenvatting()
                
                # Grafiek maken
                buf = genereer_grafiek_afbeelding()
                
                # Naar iedereen sturen
                for chat_id in TELEGRAM_CHAT_IDS:
                    stuur_telegram_bericht(tekst, chat_id)
                    if buf:
                        stuur_telegram_foto(buf, chat_id)
                        buf.seek(0) # Buffer terugspoelen voor volgende chat_id
                
                if buf: buf.close()
                
                dagrapport_verstuurd = True # Zodat we het niet 15 sec later nog eens doen
                logging.info("✅ Dagafsluiting succesvol verstuurd.")

            time.sleep(15)
            
        except Exception as e:
            logging.error(f"❌ Fout in loop: {e}")
            time.sleep(60)

def main():
    if not TELEGRAM_BOT_TOKEN or not ELIA_API_URL:
        logging.error("⛔ STOP: .env bestand niet correct.")
        return

    threading.Thread(target=prijscontrole_loop, daemon=True).start()
    monitor_telegram()

if __name__ == "__main__":
    main()