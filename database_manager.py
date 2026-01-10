import sqlite3
import logging
from datetime import datetime, timedelta
import config

def init_database():
    try:
        conn = sqlite3.connect(config.DB_BESTAND)
        c = conn.cursor()
        
        # Tabel 1: Dagstatistieken (1 rij per dag)
        c.execute('''
            CREATE TABLE IF NOT EXISTS dagstatistieken (
                datum TEXT PRIMARY KEY,
                laagste REAL,
                hoogste REAL,
                gemiddelde REAL,
                mediaan REAL,             
                aantal INTEGER,
                aantal_negatief INTEGER,
                aantal_duur INTEGER,
                tijdstip_laagste TEXT,
                tijdstip_hoogste TEXT     
            )
        ''')

        # Tabel 2: Detail metingen (elke minuut een rij)
        c.execute('''
            CREATE TABLE IF NOT EXISTS metingen_detail (
                datum TEXT,
                tijd TEXT,
                waarde REAL
            )
        ''')
        
        c.execute('CREATE INDEX IF NOT EXISTS idx_detail_datum ON metingen_detail (datum)')
        
        conn.commit()
        conn.close()
        logging.info("📚 Database tabellen gecontroleerd.")
    except Exception as e:
        logging.error(f"❌ Fout bij init DB: {e}")

def sla_buffer_en_dag_op(dag_data, minuut_buffer):
    """ 
    Deze functie doet het zware werk elke 15 minuten.
    1. Hij schrijft de buffer (lijst met minuutwaardes) weg in metingen_detail.
    2. Hij update de dagstatistieken.
    """
    try:
        conn = sqlite3.connect(config.DB_BESTAND)
        c = conn.cursor()
        
        # 1. Bulk insert van de buffer (de losse minuten)
        # minuut_buffer is een lijst van tuples: [('2023-10-27', '14:00', 50.5), ('2023-10-27', '14:01', 52.0), ...]
        if minuut_buffer:
            c.executemany('INSERT INTO metingen_detail (datum, tijd, waarde) VALUES (?, ?, ?)', minuut_buffer)

        # 2. Update de dagstatistieken (de samenvatting)
        # We pakken de waardes uit de dictionary 'dag_data'
        c.execute('''
            INSERT OR REPLACE INTO dagstatistieken 
            (datum, laagste, hoogste, gemiddelde, mediaan, aantal, aantal_negatief, aantal_duur, tijdstip_laagste, tijdstip_hoogste)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            dag_data['datum'], dag_data['laagste'], dag_data['hoogste'], 
            dag_data['gemiddelde'], dag_data['mediaan'], dag_data['aantal'], 
            dag_data['aantal_negatief'], dag_data['aantal_duur'], 
            dag_data['tijd_laag'], dag_data['tijd_hoog']
        ))
        
        conn.commit()
        conn.close()
        logging.info(f"💾 Opslag gereed: {len(minuut_buffer)} minuut-regels weggeschreven & dagstats geüpdatet.")
    except Exception as e:
        logging.error(f"❌ Fout bij opslaan database: {e}")

def haal_vandaag_op(datum_str):
    """
    Wordt gebruikt bij OPSTARTEN.
    Haalt alle minuut-metingen van vandaag op uit de DB om het geheugen te herstellen.
    """
    try:
        conn = sqlite3.connect(config.DB_BESTAND)
        c = conn.cursor()
        c.execute("SELECT tijd, waarde FROM metingen_detail WHERE datum = ? ORDER BY tijd ASC", (datum_str,))
        rijen = c.fetchall() # Geeft lijst terug: [('00:01', 50.0), ('00:02', 51.0)...]
        conn.close()
        return rijen
    except Exception as e:
        logging.error(f"❌ Fout bij ophalen hersteldata: {e}")
        return []