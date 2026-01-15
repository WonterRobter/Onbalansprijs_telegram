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
        
        # Buffer uit RAM lezen (alleen voor Vandaag)
        vandaag_str = datetime.now().strftime('%Y-%m-%d')
        if datum_str == vandaag_str:
            pad = '/dev/shm/energy_live.json' if os.path.exists('/dev/shm') else 'energy_live.json'
            if os.path.exists(pad):
                try:
                    with open(pad, 'r') as f:
                        buffer_data = json.load(f)
                        if buffer_data:
                            df_buffer = pd.DataFrame(buffer_data, columns=['datum', 'tijd', 'waarde'])
                            df_buffer = df_buffer[['tijd', 'waarde']]
                            df = pd.concat([df, df_buffer], ignore_index=True)
                            df = df.drop_duplicates(subset=['tijd'], keep='last')
                except Exception as e:
                    print(f"Kon buffer niet lezen: {e}")
        
        if not df.empty:
            # Minuut statistieken
            huidige_prijs = df.iloc[-1]['waarde']
            gemiddelde_vandaag = df['waarde'].mean()
            delta_prijs = huidige_prijs - gemiddelde_vandaag
            
            delta_avg = 0
            if avg_gisteren is not None:
                delta_avg = gemiddelde_vandaag - avg_gisteren

            # Kwartier (Settlement) statistieken
            tele_df = df[df['tijd'].str.endswith(('14','29','44','59'))]
            
            if not tele_df.empty:
                tele_gem = round(tele_df['waarde'].mean(), 2)
                tele_min = round(tele_df['waarde'].min(), 2)
                tele_max = round(tele_df['waarde'].max(), 2)
                # NIEUW: Verschil berekenen (Kwartier Gem vs Dag Gem)
                delta_tele = tele_gem - gemiddelde_vandaag
                if avg_gisteren is not None:
                    delta_tele = tele_gem - avg_gisteren

            return {
                "datum": datum_str, 
                "full": { "tijden": df['tijd'].tolist(), "prijzen": df['waarde'].tolist() },
                "tele": { "tijden": tele_df['tijd'].tolist(), "prijzen": tele_df['waarde'].tolist() },
                "huidig": df.iloc[-1].to_dict(),
                "stats": { 
                    # Alles naar INT (geheel getal)
                    "gem": int(round(gemiddelde_vandaag)), 
                    "min": int(round(df['waarde'].min())), 
                    "max": int(round(df['waarde'].max())), 
                    "delta_prijs": int(round(delta_prijs)),
                    "delta_avg": int(round(delta_avg)),
                    "avg_gisteren": avg_gisteren,
                    "limits": { "duur": config.GRENS_DUUR, "negatief": config.GRENS_NEGATIEF },
                    
                    "tele_gem": int(round(tele_gem)),
                    "tele_min": int(round(tele_min)),
                    "tele_max": int(round(tele_max)),
                    "delta_tele": int(round(delta_tele))
                }
            }
        return {"datum": datum_str, "error": "Geen data"}
    except Exception as e: 
        print(f"Fout: {e}")
        return None

def haal_maand_data(gekozen_maand=None):
    """
    Haalt data op voor de maand-pagina.
    """
    try:
        if gekozen_maand is None:
            gekozen_maand = datetime.now().strftime('%Y-%m')
            
        conn = sqlite3.connect(config.DB_BESTAND)
        # Filter op de specifieke maand
        query = """
            SELECT * FROM dagstatistieken 
            WHERE strftime('%Y-%m', datum) = ? 
            ORDER BY datum ASC
        """
        df = pd.read_sql_query(query, conn, params=(gekozen_maand,))
        conn.close()
        
        result = {"maand": gekozen_maand}
        
        if not df.empty:
            df['normaal'] = df['aantal'] - df['aantal_negatief'] - df['aantal_duur']
            df['gemist'] = (1440 - df['aantal']).clip(lower=0)
            
            df['gemiddelde'] = df['gemiddelde'].round(0).astype(int)
            df['laagste'] = df['laagste'].round(0).astype(int)
            df['hoogste'] = df['hoogste'].round(0).astype(int)
            
            result.update(df.to_dict(orient='list'))
            return result
            
        return result
    except Exception as e:
        print(f"Error maand: {e}")
        return None

def haal_jaar_data(gekozen_jaar=None):
    """
    Haalt data op voor de jaar-pagina.
    """
    try:
        if gekozen_jaar is None:
            gekozen_jaar = datetime.now().strftime('%Y')

        conn = sqlite3.connect(config.DB_BESTAND)
        query = """
            SELECT strftime('%Y-%m', datum) as maand,
                   AVG(gemiddelde) as gem_prijs, MIN(laagste) as laagste, MAX(hoogste) as hoogste,
                   SUM(aantal_negatief) as som_negatief, SUM(aantal_duur) as som_duur
            FROM dagstatistieken 
            WHERE strftime('%Y', datum) = ?
            GROUP BY maand ORDER BY maand ASC
        """
        df = pd.read_sql_query(query, conn, params=(gekozen_jaar,))
        conn.close()
        
        result = {"jaar": gekozen_jaar}
        
        if not df.empty:
            df['uren_negatief'] = (df['som_negatief'] / 60).round(1) # Uren mogen wel 1 decimaal houden
            df['uren_duur'] = (df['som_duur'] / 60).round(1)
            
            # Prijs naar geheel getal
            df['gem_prijs'] = df['gem_prijs'].round(0).astype(int)
            
            result.update(df.to_dict(orient='list'))
            return result
            
        return result
    except Exception as e: 
        print(f"Error jaar: {e}")
        return None

# --- ROUTES ---

@app.route('/')
def page_vandaag():
    gekozen_datum = request.args.get('datum') 
    data = haal_live_data(gekozen_datum)
    vandaag_str = datetime.now().strftime('%Y-%m-%d')
    # Check of data bestaat voordat we de datum vergelijken
    is_live = False
    if data and 'datum' in data:
        is_live = (data['datum'] == vandaag_str)

    return render_template('index.html', active_page='vandaag', data=data, is_live=is_live)

@app.route('/maand')
def page_maand():
    maand = request.args.get('maand') 
    return render_template('index.html', active_page='maand', history=haal_maand_data(maand))

@app.route('/jaar')
def page_jaar():
    jaar = request.args.get('jaar') 
    return render_template('index.html', active_page='jaar', year=haal_jaar_data(jaar))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)