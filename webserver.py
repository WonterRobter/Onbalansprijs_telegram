from flask import Flask, render_template, jsonify, request
import sqlite3
import pandas as pd
import config
import json
import os
from datetime import datetime, timedelta

app = Flask(__name__)

# --- DATABANK FUNCTIES ---

def haal_live_data(datum_str=None):
    """ 
    DATA VOOR: DAG DETAILS (Minuut per minuut) 
    Als datum_str None is, pakken we vandaag.
    """
    try:
        if datum_str is None:
            datum_str = datetime.now().strftime('%Y-%m-%d')
        
        # We moeten weten wat 'gisteren' was ten opzichte van de GEKOZEN datum
        gekozen_datum = datetime.strptime(datum_str, '%Y-%m-%d')
        gisteren_str = (gekozen_datum - timedelta(days=1)).strftime('%Y-%m-%d')

        conn = sqlite3.connect(config.DB_BESTAND)
        
        # 1. Haal data van de GEKOZEN datum
        df = pd.read_sql_query("SELECT tijd, waarde FROM metingen_detail WHERE datum = ? ORDER BY tijd ASC", conn, params=(datum_str,))
        
        # 2. Haal gemiddelde van de dag ERVOOR
        cursor = conn.cursor()
        cursor.execute("SELECT gemiddelde FROM dagstatistieken WHERE datum = ?", (gisteren_str,))
        row = cursor.fetchone()
        avg_gisteren = row[0] if row else None
        
        conn.close()
        
        # Alleen doen als we naar VANDAAG kijken
        vandaag_str = datetime.now().strftime('%Y-%m-%d')
        if datum_str == vandaag_str:
            pad = '/dev/shm/energy_live.json' if os.path.exists('/dev/shm') else 'energy_live.json'
            if os.path.exists(pad):
                try:
                    with open(pad, 'r') as f:
                        buffer_data = json.load(f)
                        # Buffer data is: [[datum, tijd, waarde], ...]
                        # We maken er een DataFrame van en plakken het vast
                        if buffer_data:
                            df_buffer = pd.DataFrame(buffer_data, columns=['datum', 'tijd', 'waarde'])
                            # Alleen tijd en waarde zijn nodig
                            df_buffer = df_buffer[['tijd', 'waarde']]
                            
                            # Plakken aan de bestaande data (concat)
                            df = pd.concat([df, df_buffer], ignore_index=True)
                            
                            # Dubbele waarden verwijderen (voor de zekerheid)
                            df = df.drop_duplicates(subset=['tijd'], keep='last')
                except Exception as e:
                    print(f"Kon buffer niet lezen: {e}")
        
        if not df.empty:
            tele_df = df[df['tijd'].str.endswith(('14','29','44','59'))]
            huidige_prijs = df.iloc[-1]['waarde']
            gemiddelde_vandaag = df['waarde'].mean()
            delta_prijs = huidige_prijs - gemiddelde_vandaag
            
            delta_avg = 0
            if avg_gisteren is not None:
                delta_avg = gemiddelde_vandaag - avg_gisteren
            
            return {
                "datum": datum_str, # We sturen de datum mee terug voor de titel
                "full": { "tijden": df['tijd'].tolist(), "prijzen": df['waarde'].tolist() },
                "tele": { "tijden": tele_df['tijd'].tolist(), "prijzen": tele_df['waarde'].tolist() },
                "huidig": df.iloc[-1].to_dict(),
                "stats": { 
                    "gem": round(gemiddelde_vandaag, 2), 
                    "min": round(df['waarde'].min(), 2), 
                    "max": round(df['waarde'].max(), 2), 
                    "delta_prijs": round(delta_prijs, 2),
                    "delta_avg": round(delta_avg, 2),
                    "avg_gisteren": avg_gisteren,
                    "limits": { "duur": config.GRENS_DUUR, "negatief": config.GRENS_NEGATIEF }
                }
            }
        # Als er geen data is, sturen we toch de datum terug zodat de datumkiezer niet leeg is
        return {"datum": datum_str, "error": "Geen data"}
    except Exception as e: 
        print(f"Fout: {e}")
        return None

def haal_maand_data():
    try:
        conn = sqlite3.connect(config.DB_BESTAND)
        df = pd.read_sql_query("SELECT * FROM dagstatistieken ORDER BY datum ASC LIMIT 31", conn)
        conn.close()
        if not df.empty:
            df['normaal'] = df['aantal'] - df['aantal_negatief'] - df['aantal_duur']
            df['gemist'] = (1440 - df['aantal']).clip(lower=0)
            return df.to_dict(orient='list')
        return None
    except: return None

def haal_jaar_data():
    try:
        conn = sqlite3.connect(config.DB_BESTAND)
        query = """
            SELECT strftime('%Y-%m', datum) as maand,
                   AVG(gemiddelde) as gem_prijs, MIN(laagste) as laagste, MAX(hoogste) as hoogste,
                   SUM(aantal_negatief) as som_negatief, SUM(aantal_duur) as som_duur
            FROM dagstatistieken GROUP BY maand ORDER BY maand ASC LIMIT 12
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        if not df.empty:
            df['uren_negatief'] = (df['som_negatief'] / 60).round(1)
            df['uren_duur'] = (df['som_duur'] / 60).round(1)
            df['gem_prijs'] = df['gem_prijs'].round(2)
            return df.to_dict(orient='list')
        return None
    except: return None

# --- ROUTES ---

@app.route('/')
def page_vandaag():
    # We kijken of er een datum in de URL staat (bv: /?datum=2026-01-01)
    gekozen_datum = request.args.get('datum') 
    
    # Haal data op (als gekozen_datum None is, pakt de functie zelf Vandaag)
    data = haal_live_data(gekozen_datum)
    
    # Check of het VANDAAG is (voor de auto-refresh)
    vandaag_str = datetime.now().strftime('%Y-%m-%d')
    is_live = (data['datum'] == vandaag_str)

    return render_template('index.html', 
                           active_page='vandaag', 
                           data=data, 
                           is_live=is_live) # We vertellen de HTML of de refresh aan moet

@app.route('/maand')
def page_maand():
    return render_template('index.html', active_page='maand', history=haal_maand_data())

@app.route('/jaar')
def page_jaar():
    return render_template('index.html', active_page='jaar', year=haal_jaar_data())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)