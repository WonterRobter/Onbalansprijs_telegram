import sqlite3
import logging

DB_BESTAND = 'onbalans_historiek.db'

def init_database():
    try:
        conn = sqlite3.connect(DB_BESTAND)
        c = conn.cursor()
        # NIEUW: Uitgebreide tabel structuur
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
        conn.commit()
        conn.close()
        logging.info("📚 Database gecontroleerd/aangemaakt met nieuwe kolommen.")
    except Exception as e:
        logging.error(f"❌ Fout bij initialiseren database: {e}")

# NIEUW: Functie accepteert nu veel meer argumenten
def sla_dag_op_in_db(datum, laagste, hoogste, gemiddelde, mediaan, aantal, aantal_negatief, aantal_duur, tijd_laag, tijd_hoog):
    try:
        conn = sqlite3.connect(DB_BESTAND)
        c = conn.cursor()
        
        c.execute('''
            INSERT OR REPLACE INTO dagstatistieken 
            (datum, laagste, hoogste, gemiddelde, mediaan, aantal, aantal_negatief, aantal_duur, tijdstip_laagste, tijdstip_hoogste)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (datum, laagste, hoogste, gemiddelde, mediaan, aantal, aantal_negatief, aantal_duur, tijd_laag, tijd_hoog))
        
        conn.commit()
        conn.close()
        logging.info(f"💾 Data voor {datum} opgeslagen (Mediaan: {mediaan}, Min om {tijd_laag}, Max om {tijd_hoog}).")
    except Exception as e:
        logging.error(f"❌ Fout bij opslaan in database: {e}")