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
   ```

   **Uitleg:**
   
   - `TELEGRAM_BOT_TOKEN` → Verkregen via [@BotFather](https://t.me/BotFather)  
   - `TELEGRAM_CHAT_IDS` → Komma-gescheiden lijst met Telegram-chat-ID’s die meldingen ontvangen  
   - `ELIA_API_URL` → API-endpoint voor onbalansprijzen (Elia)
   
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
   ExecStart=/usr/bin/python3 /home/wouter/telegram_bot/raspberryonbalansprij>WorkingDirectory=/home/wouter/telegram_bot
   Restart=always
   RestartSec=5
   User=wouter
   Environment=PYTHONUNBUFFERED=1

   [Install]
   WantedBy=multi-user.target

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

## 📜 Licentie

Dit project valt onder de [MIT License](./LICENSE).  
Vrij te gebruiken en aan te passen — geef graag een vermelding naar de originele auteur.

---

## 💡 Credits

Ontwikkeld door **Wouter**  
🧠 Gebouwd voor **energie-enthousiastelingen** die realtime inzicht willen in de Belgische onbalansprijzen.
