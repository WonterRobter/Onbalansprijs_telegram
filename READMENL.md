# ⚡ Elia Onbalansprijs Telegram Bot

Een Python-script dat de **onbalansprijzen** van de Belgische netbeheerder **Elia** automatisch ophaalt en **meldingen stuurt via Telegram** bij extreme prijsveranderingen.  
Het script is geoptimaliseerd om **continu te draaien op een Raspberry Pi**.

---

## 🧠 Functionaliteit

- 📡 Haalt onbalansprijzen op via de **Elia API**
- 🤖 Stuurt Telegram-meldingen bij prijsdrempels:
  - ⚠️ Onder 50 €/MWh  
  - ✅ Onder 0 €/MWh  
  - 🌟 Onder -50 €/MWh  
  - ❄️ Zeer laag (< -150 €/MWh)  
  - 🧊 Extreem laag (< -500 €/MWh)  
  - 🚨 Zeer hoog (> 400 €/MWh)
- 🔁 Meldt wanneer de server of Raspberry herstart
- 💬 Reageert op het Telegram-commando `/price` met de huidige prijs
- 🔒 Fouttolerant dankzij retries, logging en backoff-logica
- 🗂️ Modulair opgezet: aparte bestanden voor API, Telegram, prijslogica en monitoring

---

## 📂 Projectstructuur

```
Onbalansprijs_telegram/
├── onbalansprijs/
│   ├── __init__.py          # Maakt van de map een Python package
│   ├── elia_api.py          # Haalt prijzen op via de Elia API
│   ├── telegram_bot.py      # Stuurt en ontvangt berichten via Telegram
│   ├── prijs_logic.py       # Vergelijkt prijzen en beslist welke meldingen nodig zijn
│   ├── price_monitor.py     # Loops en threads die alles laten draaien
│   └── logging_helpers.py   # Logging en gedeelde sessie
├── config.py                # Leest configuratie uit .env bestand
├── main.py                  # Startpunt van de applicatie
├── requirements.txt         # Dependencies
└── .env.example             # Voorbeeld van vereiste variabelen
```

---

## 🧩 Installatie

1. Clone deze repository:

   ```bash
   git clone https://github.com/WonterRobter/Onbalansprijs_telegram.git
   cd Onbalansprijs_telegram
   ```

2. Installeer vereisten:

   ```bash
   sudo apt update
   sudo apt install python3-pip -y
   pip install -r requirements.txt
   ```

3. ⚙️ Configuratie  
   Maak een `.env` bestand in de hoofdmap met de volgende inhoud:

   ```env
   TELEGRAM_BOT_TOKEN=je_bot_token
   TELEGRAM_CHAT_IDS=123456789,987654321
   ELIA_API_URL=https://api.elia.be/...   # Het endpoint dat je gebruikt
   LOG_LEVEL=INFO
   ```

   **Uitleg:**
   - `TELEGRAM_BOT_TOKEN` → Verkregen via [@BotFather](https://t.me/BotFather)  
   - `TELEGRAM_CHAT_IDS` → Komma-gescheiden lijst met Telegram-chat-ID’s die meldingen ontvangen  
   - `ELIA_API_URL` → API-endpoint voor onbalansprijzen (Elia) of je test-API  
   - `LOG_LEVEL` → Optioneel, standaard `INFO`  

   ⚠️ Vergeet niet `.env` toe te voegen aan je `.gitignore`, zodat je gevoelige gegevens niet per ongeluk uploadt naar GitHub.

4. 🚀 Gebruik / draaien  
   Start de bot:

   ```bash
   python3 main.py
   ```

   De bot blijft lopen en controleert elke ~15 seconden de actuele prijs.  
   Hij stuurt meldingen bij veranderingen volgens jouw ingestelde drempelwaarden.

---

## 🔁 Automatisch starten via systemd (Raspberry Pi)

Je kunt de bot automatisch starten na elke reboot met een systemd-service:

1. Maak een servicebestand:

   ```bash
   sudo nano /etc/systemd/system/elia-bot.service
   ```

2. Voeg deze inhoud toe:

   ```ini
   [Unit]
   Description=Telegram Bot Service
   After=network-online.target
   Wants=network-online.target

   [Service]
   ExecStart=/usr/bin/python3 /home/pi/Onbalansprijs_telegram/main.py
   WorkingDirectory=/home/pi/Onbalansprijs_telegram
   Restart=always
   RestartSec=5
   User=pi
   Environment=PYTHONUNBUFFERED=1

   [Install]
   WantedBy=multi-user.target
   ```

3. Activeer de service:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable elia-bot
   sudo systemctl start elia-bot
   ```

4. Controleer de status:

   ```bash
   sudo systemctl status elia-bot
   ```

   **Of volg de logs live:**

   ```bash
   journalctl -u elia-bot -f
   ```

---

## 📦 Requirements

Maak een bestand aan met de naam `requirements.txt` en voeg het volgende toe:

```
requests
python-dotenv
pytz
```

---

## 🚫 .gitignore

Voeg dit bestand toe met de naam `.gitignore` om gevoelige of overbodige bestanden te negeren:

```
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.env

# Editor / IDE
.vscode/
.idea/
*.swp

# Logs
*.log

# OS bestanden
.DS_Store
Thumbs.db
```

---

## 📊 Voorbeeldoutput in Telegram

Bij een prijsdaling onder 0 €/MWh:
```
✅ Onbalansprijs onder 0 : -12 €/MWh
🕒 Tijd: 14:30
```

Bij een extreme prijsstijging boven 400 €/MWh:
```
🚨 ZÉÉR HOGE onbalansprijs: 425 €/MWh
🕒 Tijd: 18:45
```

Bij een reboot van de server:
```
🔄 Server herstart!: 35 €/MWh
🕒 Tijd: 09:15
```

---

## ❓ FAQ

**Wat als de API niet bereikbaar is?**  
De bot probeert opnieuw met retries en backoff. Fouten worden gelogd.

**Kan ik meerdere chat-ID’s gebruiken?**  
Ja, geef ze komma-gescheiden in `TELEGRAM_CHAT_IDS`.

**Kan ik testen zonder de echte Elia API?**  
Ja, gebruik de meegeleverde fake API (`fake_api_dynamic.py`) en zet `ELIA_API_URL=http://localhost:5000/testdata`.

**Hoe vaak wordt de prijs opgehaald?**  
Elke 15 seconden, configureerbaar in de code.

---

## 📜 Licentie

Dit project valt onder de [MIT License](./LICENSE).  
Vrij te gebruiken en aan te passen — geef graag een vermelding naar de originele auteur.

---

## 💡 Credits

Ontwikkeld door **Wouter**  
🧠 Gebouwd voor **energie-enthousiastelingen** die realtime inzicht willen in de Belgische onbalansprijzen.