import os
import time
import logging
import threading
import io
import statistics
from datetime import datetime, date, timedelta

# Externe bibliotheken
import requests
import pytz
import matplotlib
from dotenv import load_dotenv

# Importeer je aparte database bestand
import database_manager

# Matplotlib instellingen (grafieken zonder scherm)
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# =============================================================================
# 1. CONFIGURATIE & INSTELLINGEN
# =============================================================================

# Laad variabelen uit het .env bestand
load_dotenv()

# Logging configuratie (wat zie je in de console)
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# --- API & TOEGANG ---
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_IDS_RAW = os.getenv("TELEGRAM_CHAT_IDS", "")
ELIA_API_URL = os.getenv('ELIA_API_URL')

# Zet de string van chat-ID's om naar een nette lijst
TELEGRAM_CHAT_IDS = [id.strip() for id in TELEGRAM_CHAT_IDS_RAW.split(",") if id.strip()]

# --- TIJD & SESSIE ---
BELGIUM_TZ = pytz.timezone('Europe/Brussels')
session = requests.Session()

# --- PRIJSGRENSWAARDEN (Instellingen) ---
# Pas deze waardes aan om de alarmen te finetunen
GRENS_EXTREEM_LAAG = -500
GRENS_ZEER_LAAG    = -150
GRENS_LAAG_MIN_50  = -50
GRENS_NEGATIEF     = 0
GRENS_GOEDKOOP     = 50
GRENS_HERSTEL      = 60
GRENS_ZEER_HOOG    = 400

# =============================================================================
# 2. GLOBALE VARIABELEN (OPSLAG)
# =============================================================================

buffer_voor_db = []     # Buffer voor bulk opslag in DB
history_prices = []     # Opslag voor prijzen (Y-as)
history_times = []      # Opslag voor tijden (X-as)
history_negatief_count = 0
history_duur_count = 0
laatste_datum = datetime.now(BELGIUM_TZ).date()
dagrapport_verstuurd = False 

# =============================================================================
# 3. TELEGRAM FUNCTIES
# =============================================================================

def stuur_telegram_bericht(bericht, chat_id, retries=3):
    """
    Stuurt een tekstbericht naar een specifieke Telegram-gebruiker.
    Inclusief 'retry' mechanisme als het even niet lukt.
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"text": bericht, "chat_id": chat_id, "parse_mode": "HTML"}
    backoff = 2
    
    for attempt in range(retries):
        try:
            # logging.debug(f"Poging {attempt+1}: Verstuur bericht naar {chat_id}")
            response = session.post(url, json=payload, timeout=10)
            response.raise_for_status() # Geeft een fout als de statuscode niet 200 is
            
            logging.info(f"✅ Bericht verzonden naar {chat_id}")
            break
        except requests.exceptions.RequestException as e:
            logging.error(f"❌ Fout bij verzenden bericht (poging {attempt+1}): {e}")
            if attempt < retries - 1:
                time.sleep(backoff)
                backoff *= 2

def stuur_telegram_foto(photo_buffer, chat_id):
    """ Stuurt een afbeelding (grafiek) naar Telegram """
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

# =============================================================================
# 4. DATA & GRAFIEK GENERATIE
# =============================================================================

def doe_http_aanroep(url, retries=3, timeout=10):
    """ Haalt data op van de Elia API met foutafhandeling. """
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
    if len(history_prices) < 2:
        return None

    try:
        plot_times = []
        plot_prices = []
        
        # We maken een tijdelijke dictionary om dubbele punten in dezelfde minuut te voorkomen
        # Key = "14:14", Value = (tijd, prijs)
        unieke_punten = {}

        for t, p in zip(history_times, history_prices):
            # De strenge filter: Alleen xx:14, xx:29, xx:44, xx:59
            if t.minute % 15 == 14:
                tijd_key = t.strftime('%H:%M')
                unieke_punten[tijd_key] = (t, p)

        # Nu de gefilterde punten weer in een lijst zetten
        for key in unieke_punten:
            t, p = unieke_punten[key]
            plot_times.append(t)
            plot_prices.append(p)

        # Check: Hebben we na het filteren wel genoeg punten voor een lijn?
        if len(plot_prices) < 2:
            logging.info(f"Grafiek: Wel data, maar na filteren nog te weinig kwartier-punten ({len(plot_prices)}). Even geduld.")
            return None
        
        # --- De rest is standaard grafiek code ---
        plt.figure(figsize=(10, 5))
        plt.plot(plot_times, plot_prices, color='blue', linewidth=2, marker='o', markersize=4)
        
        titel_datum = datetime.now(BELGIUM_TZ).strftime('%d-%m-%Y')
        plt.title(f"Settlement Prijzen ({titel_datum})")
        plt.ylabel("Prijs (€\\MWh)")
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # X-as formateren (Tijd)
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M', tz=BELGIUM_TZ))
        plt.gcf().autofmt_xdate()
        plt.axhline(0, color='red', linewidth=1, linestyle='-') # Rode lijn op 0

        # Opslaan in buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close()
        buf.seek(0)
        return buf

    except Exception as e:
        logging.error(f"Fout in grafiek generatie: {e}")
        return None

def genereer_dag_samenvatting():
    """ Berekent statistieken (min, max, gem) voor het dagoverzicht. """
    global history_negatief_count, history_duur_count
    
    if not history_prices:
        return "📉 Nog geen metingen verzameld vandaag."
    
    laagste = round(min(history_prices))
    hoogste = round(max(history_prices))
    gemiddelde = round(sum(history_prices) / len(history_prices))
    
    return (
        f"🏁 <b>📊 Overzicht Vandaag</b>\n\n"
        f"📉 Laagste: <b>{laagste} €\\MWh</b>\n"
        f"📈 Hoogste: <b>{hoogste} €\\MWh</b>\n"
        f"⚖️ Gemiddeld: <b>{gemiddelde} €\\MWh</b>\n\n"
        f"⏱️ Negatief: <b>{history_negatief_count} min</b>\n"
        f"💸 Duur (>100): <b>{history_duur_count} min</b>\n"
        f"📊 Totaal metingen: {len(history_prices)}"
    )

# =============================================================================
# 5. LOGICA (PRIJS & STATUS)
# =============================================================================

def haal_onbalansprijs_op():
    """ Haalt de huidige prijs en tijdstip op uit de API data. """
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
    Checkt of de prijs een bepaalde grens overschrijdt en stuurt alarmen.
    Houdt de 'status' bij om te voorkomen dat we blijven spammen.
    """
    prijs = round(prijs)
    tijd_str = f"{timestamp_obj.hour}:{timestamp_obj.minute:02}"

    # Alleen loggen in console als prijs verandert
    if prijs != laatste_prijs:
        logging.info(f"📊 Nieuwe prijs: {prijs} €\\MWh ({tijd_str})")

    def meld(titel, icoon):
        """ Helper om snel berichten te sturen naar alle chats """
        bericht = f"{icoon} <b>{titel}:</b> {prijs} €\\MWh\n <i>{tijd_str}</i>"
        for chat_id in TELEGRAM_CHAT_IDS:
            stuur_telegram_bericht(bericht, chat_id)

    # --- STATUS CHECKS ---
    
    # 1. Extreem Laag
    if prijs < GRENS_EXTREEM_LAAG and not status['extreem_laag']:
        meld("EXTREEM LAGE PRIJS", "🧊")
        status.update({
            'extreem_laag': True,
            'zeer_laag': True,
            'onder_min_50': True,
            'onder_0': True,
            'onder_50': True,
            'zeer_hoog': False
            })
        return prijs, status
        
    # 2. Zeer Laag
    if prijs < GRENS_ZEER_LAAG and not status['zeer_laag']:
        meld("ZÉÉR LAGE PRIJS", "❄️")
        status.update({
            'zeer_laag': True,
            'onder_min_50': True,
            'onder_0': True,
            'onder_50': True,
            'zeer_hoog': False
        })
        return prijs, status

    # 3. Zeer Hoog
    if prijs > GRENS_ZEER_HOOG and not status['zeer_hoog']:
        meld("ZÉÉR HOGE PRIJS", "🚨")
        status.update({
            'zeer_hoog': True,
            'extreem_laag': False,
            'zeer_laag': False,
            'onder_min_50': False,
            'onder_0': False,
            'onder_50': False
        })
        return prijs, status

    # 4. Onder -50
    if prijs < GRENS_LAAG_MIN_50 and not status['onder_min_50']:
        meld("Prijs onder -50", "🌟")
        status.update({
            'onder_min_50': True,
            'onder_0': True,
            'onder_50': True,
            'zeer_hoog': False
        })
        return prijs, status

    # 5. Negatief (onder 0)
    if prijs < GRENS_NEGATIEF and not status['onder_0']:
        meld("Prijs onder 0", "✅")
        status.update({
            'onder_0': True,
            'onder_50': True,
            'zeer_hoog': False
        })
        return prijs, status

    # 6. Goedkoop (onder 50)
    if GRENS_NEGATIEF < prijs < GRENS_GOEDKOOP and not status['onder_50']:
        meld("Prijs onder 50", "⚠️")
        status.update({
            'onder_50': True,
            'zeer_hoog': False
        })
        return prijs, status

    # --- HERSTEL MELDINGEN ---
    
    # Herstel boven 50
    if prijs >= GRENS_HERSTEL and status['onder_50']:
        meld("Prijs weer boven 50", "📈")
        status.update({
            'onder_50': False,
            'onder_0': False,
            'onder_min_50': False
        })

    # Herstel boven 0
    elif prijs >= GRENS_NEGATIEF and status['onder_0']:
        meld("Prijs weer positief", "⚠️")
        status.update({
            'onder_0': False,
            'onder_min_50': False
        })
    # Herstel boven -50
    elif prijs >= GRENS_LAAG_MIN_50 and status['onder_min_50']:
        meld("Prijs weer boven -50", "☑️")
        status.update({'onder_min_50': False})

    return prijs, status

# =============================================================================
# 6. HOOFD LOOPS
# =============================================================================

def monitor_telegram():
    """ Luistert constant naar inkomende berichten van gebruikers. """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    last_update_id = None
    logging.info("🤖 Telegram monitor gestart...")
    
    while True:
        try:
            params = {'offset': last_update_id, 'timeout': 30}
            response = session.get(url, params=params, timeout=35)
            response.raise_for_status()
            updates = response.json().get('result', [])
            
            for update in updates:
                last_update_id = update['update_id'] + 1
                message = update.get('message', {})
                tekst = message.get('text', '').strip().lower() # .lower() maakt checken makkelijker
                chat_id = message.get('chat', {}).get('id')
                
                if not chat_id: continue

                # COMMANDO: /price
                if tekst == "/price":
                    logging.info(f"📩 Commando /price van {chat_id}")
                    prijs, timestamp_obj = haal_onbalansprijs_op()
                    if prijs is not None:
                        tijd_str = f"{timestamp_obj.hour}:{timestamp_obj.minute:02}"
                        stuur_telegram_bericht(f"ℹ️ <b>Huidige prijs:</b> {round(prijs)} €\\MWh\n <i>{tijd_str}</i>", chat_id)
                    else:
                        stuur_telegram_bericht("⚠️ Kon prijs niet ophalen.", chat_id)

                # COMMANDO: /vandaag
                elif tekst == "/vandaag":
                    logging.info(f"📩 Commando /vandaag van {chat_id}")
                    stuur_telegram_bericht(genereer_dag_samenvatting(), chat_id)
                
                # COMMANDO: /grafiek
                elif tekst == "/grafiek":
                    logging.info(f"📩 Commando /grafiek van {chat_id}")
                    stuur_telegram_bericht("🎨 Grafiek wordt gemaakt...", chat_id)
                    buf = genereer_grafiek_afbeelding()
                    if buf:
                        stuur_telegram_foto(buf, chat_id)
                        buf.close()
                    else:
                        stuur_telegram_bericht("📉 Te weinig data voor grafiek.", chat_id)
            
            time.sleep(1)

        except Exception as e:
            logging.error(f"Telegram loop fout: {e}")
            time.sleep(5)

def prijscontrole_loop():
    """ 
    De motor van het script: haalt elke 15s de prijs op.
    AANGEPAST: Gebruikt nu API-tijd in plaats van Systeem-tijd voor opslag.
    """
    global history_prices, history_times, buffer_voor_db, laatste_datum, dagrapport_verstuurd
    global history_negatief_count, history_duur_count
    
    laatste_prijs = None
    laatste_minuut_id = None # Om te checken of de minuut voorbij is
    
    # Start status (alles False)
    status = {
        'onder_50': False,
        'onder_0': False,
        'onder_min_50': False, 
        'zeer_laag': False,
        'extreem_laag': False,
        'zeer_hoog': False
    }

    logging.info("⚡ Prijscontrole gestart...")
    
    # Melding bij opstarten
    prijs, timestamp_obj = haal_onbalansprijs_op()
    if prijs is not None:
        tijd_str = f"{timestamp_obj.hour}:{timestamp_obj.minute:02}"
        for chat_id in TELEGRAM_CHAT_IDS:
            stuur_telegram_bericht(f'🔄 <b>Server herstart</b> {round(prijs)} €\\MWh\n<i>{tijd_str}</i>', chat_id)

    while True:
        try:
            # We houden 'nu' alleen nog voor systeem-taken (zoals middernacht checken)
            nu = datetime.now(BELGIUM_TZ)
            prijs, timestamp_obj = haal_onbalansprijs_op()
            
            if prijs is not None and timestamp_obj is not None:
                
                # 1. Check op nieuwe dag (op basis van API tijd, dat is wel zo zuiver)
                datum_api = timestamp_obj.date()
                if datum_api != laatste_datum:
                    history_prices = []
                    history_times = []
                    buffer_voor_db = [] # Buffer ook leegmaken
                    history_negatief_count = 0
                    history_duur_count = 0
                    laatste_datum = datum_api
                    dagrapport_verstuurd = False
                    logging.info(f"📅 Nieuwe dag ({datum_api}): tellers gereset.")

                # 2. Opslaan in werkgeheugen
                # BELANGRIJK: We kijken nu naar de minuut van de API (timestamp_obj)
                huidige_minuut_id = timestamp_obj.strftime('%H:%M')
                
                # Als de API een nieuwe minuut doorgeeft die we nog niet hadden:
                if huidige_minuut_id != laatste_minuut_id:
                    # == DIT IS HET "ELKE MINUUT" MOMENT ==
                    laatste_minuut_id = huidige_minuut_id
                    
                    # A. Voeg toe aan live grafiek data (gebruik API tijd!)
                    history_prices.append(prijs)
                    history_times.append(timestamp_obj) 
                    
                    # B. Update tellers
                    if prijs < 0: history_negatief_count += 1
                    if prijs > 100: history_duur_count += 1
                    
                    # C. Buffer vullen met de JUISTE tijd
                    datum_str = timestamp_obj.strftime('%Y-%m-%d')
                    buffer_voor_db.append( (datum_str, huidige_minuut_id, prijs) )
                    
                    logging.info(f"⏱️ Minuutmeting gebufferd: {prijs} (Tijdstip: {huidige_minuut_id})")

                # 3. Status updates (Alarmen mogen wel direct afgaan)
                laatste_prijs, status = beheer_prijsstatus(prijs, laatste_prijs, status, timestamp_obj)

                # 4. DATABASE UPDATE (Checken we wel op basis van systeemklok 'nu' om de 15 min)
                if nu.minute % 15 == 0 and nu.second < 20:
                    if buffer_voor_db:
                        logging.info("💾 15 minuten voorbij: Buffer wegschrijven naar DB...")
                        
                        # Bereken statistieken
                        laagste = round(min(history_prices))
                        hoogste = round(max(history_prices))
                        gem = round(sum(history_prices) / len(history_prices))
                        mediaan = round(statistics.median(history_prices))
                        
                        idx_laag = history_prices.index(min(history_prices))
                        tijd_laag = history_times[idx_laag].strftime('%H:%M')
                        idx_hoog = history_prices.index(max(history_prices))
                        tijd_hoog = history_times[idx_hoog].strftime('%H:%M')
                        
                        # We gebruiken de datum van de API data voor de statistiek
                        statistiek_datum = history_times[-1].strftime('%Y-%m-%d')

                        dag_data = {
                            'datum': statistiek_datum,
                            'laagste': laagste, 'hoogste': hoogste,
                            'gemiddelde': gem, 'mediaan': mediaan,
                            'aantal': len(history_prices),
                            'aantal_negatief': history_negatief_count,
                            'aantal_duur': history_duur_count,
                            'tijd_laag': tijd_laag, 'tijd_hoog': tijd_hoog
                        }
                        
                        database_manager.sla_buffer_en_dag_op(dag_data, buffer_voor_db)
                        buffer_voor_db = [] 
                        logging.info("✅ Database update succesvol.")
                        time.sleep(20)

            # 5. DAGAFSLUITING (Op basis van systeemklok, want we willen om 23:59 sturen)
            if nu.hour == 23 and nu.minute == 59 and not dagrapport_verstuurd:
                logging.info("🕛 Tijd voor dagafsluiting!")
                
                if history_prices and buffer_voor_db:
                    try:
                        # (Zelfde logica als hierboven voor laatste save)
                        laagste = round(min(history_prices))
                        hoogste = round(max(history_prices))
                        gem = round(sum(history_prices) / len(history_prices))
                        mediaan = round(statistics.median(history_prices))
                        idx_laag = history_prices.index(min(history_prices))
                        tijd_laag = history_times[idx_laag].strftime('%H:%M')
                        idx_hoog = history_prices.index(max(history_prices))
                        tijd_hoog = history_times[idx_hoog].strftime('%H:%M')
                        statistiek_datum = history_times[-1].strftime('%Y-%m-%d')

                        dag_data = {
                            'datum': statistiek_datum,
                            'laagste': laagste, 'hoogste': hoogste,
                            'gemiddelde': gem, 'mediaan': mediaan,
                            'aantal': len(history_prices),
                            'aantal_negatief': history_negatief_count,
                            'aantal_duur': history_duur_count,
                            'tijd_laag': tijd_laag, 'tijd_hoog': tijd_hoog
                        }
                        
                        # Opslaan!
                        database_manager.sla_buffer_en_dag_op(dag_data, buffer_voor_db)
                        buffer_voor_db = [] # Buffer legen
                    except Exception as e:
                        logging.error(f"Save fout: {e}")

                # B. Telegram Rapport Sturen
                tekst = genereer_dag_samenvatting()
                buf = genereer_grafiek_afbeelding()

                for chat_id in TELEGRAM_CHAT_IDS:
                    stuur_telegram_bericht(tekst, chat_id)
                    if buf:
                        stuur_telegram_foto(buf, chat_id); buf.seek(0)
                if buf: buf.close()
                dagrapport_verstuurd = True
            
            # Reset vlaggetje na middernacht (00:00:xx)
            if nu.hour == 0 and dagrapport_verstuurd:
                dagrapport_verstuurd = False

            time.sleep(15) # Korte slaap voor de volgende check
        except Exception as e:
            logging.error(f"Loop fout: {e}")
            time.sleep(30)

# =============================================================================
# 7. MAIN STARTPUNT
# =============================================================================

def main():
    global history_prices, history_times, history_negatief_count, history_duur_count
    if not TELEGRAM_BOT_TOKEN or not ELIA_API_URL:
        logging.error("⛔ STOP: .env bestand mist variabelen of bestaat niet.")
        return
    
    # NIEUW: Zorg dat de database klaarstaat
    database_manager.init_database()
    
    # 1. SCHOONMAAK (1 maand regel)
    database_manager.opruimen_oude_data()
    
    # 2. HERSTEL (Het 16:00 probleem oplossen)
    logging.info("♻️ Data van vandaag herstellen uit DB...")
    vandaag_str = datetime.now(BELGIUM_TZ).strftime('%Y-%m-%d')
    
    oude_data = database_manager.haal_vandaag_op(vandaag_str)
    
    if oude_data:
        logging.info(f"🔄 {len(oude_data)} metingen gevonden. Herstellen...")
        for tijd_str, prijs in oude_data:
            # Herstel de lijsten
            u, m = map(int, tijd_str.split(':'))
            tijd_obj = datetime.now(BELGIUM_TZ).replace(hour=u, minute=m, second=0, microsecond=0)
            
            history_prices.append(prijs)
            history_times.append(tijd_obj)
            
            # Herstel de tellers (ongeveer)
            if prijs < 0: history_negatief_count += 1
            if prijs > 100: history_duur_count += 1
        
        logging.info("✅ Geheugen succesvol hersteld! Dagstatistieken lopen door.")
    else:
        logging.info("✨ Geen data van vandaag gevonden. Start blanco.")
    
    # Start de prijscontrole in een aparte thread (zodat ze tegelijk draaien)
    prijs_thread = threading.Thread(target=prijscontrole_loop, daemon=True)
    prijs_thread.start()

    # Start de Telegram luisteraar (deze houdt het script 'levend')
    monitor_telegram()

if __name__ == "__main__":
    main()