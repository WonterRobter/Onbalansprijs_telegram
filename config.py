# ==========================================
# ⚙️ CONFIGURATIE BESTAND
# ==========================================

# --- DATABASE ---
DB_BESTAND = 'onbalans_historiek.db'
AANTAL_DAGEN_BEWAREN = 30  # Hoe lang bewaren we de minuut-details?

# --- GRENZEN VOOR ALARMEN (in €/MWh) ---
GRENS_EXTREEM_LAAG = -500
GRENS_ZEER_LAAG    = -150
GRENS_LAAG_MIN_50  = -50
GRENS_NEGATIEF     = 0
GRENS_GOEDKOOP     = 50
GRENS_HERSTEL      = 60
GRENS_ZEER_HOOG    = 500

# --- TELLERS ---
# Boven welke prijs tellen we het als "Duur"?
GRENS_DUUR = 100