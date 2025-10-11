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
Installeer vereisten:

bash
Copy code
sudo apt update
sudo apt install python3-pip -y
pip install -r requirements.txt


⚙️ Configuratie
Maak een .env bestand in de hoofdmap met de volgende inhoud:

env
Copy code
TELEGRAM_BOT_TOKEN=je_bot_token
TELEGRAM_CHAT_IDS=123456789,987654321
ELIA_API_URL=https://api.elia.be/…   # Het endpoint dat je gebruikt
TELEGRAM_BOT_TOKEN — het token dat je krijgt via [@BotFather]

TELEGRAM_CHAT_IDS — een komma-gescheiden lijst van chat-id’s waarmee de bot werkt

ELIA_API_URL — API-endpoint voor de onbalansprijzen

Zorg dat .env in je .gitignore staat, zodat je gevoelige gegevens niet per ongeluk publiceert.


🚀 Gebruik / draaien
Start de bot:

bash
Copy code
python3 main.py
De bot blijft lopen en controleert elke ~15 seconden de actuele prijs. Hij stuurt meldingen bij veranderingen volgens jouw ingestelde drempelwaarden.


🔁 Automatisch starten via systemd (Raspberry Pi)
Je kunt de bot automatisch starten na elke reboot met een systemd-service:

Maak een servicebestand /etc/systemd/system/elia-bot.service:

ini
Copy code
[Unit]
Description=Onbalans Telegram Bot
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/Onbalansprijs_telegram/main.py
WorkingDirectory=/home/pi/Onbalansprijs_telegram
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
Activeer de service:

bash
Copy code
sudo systemctl daemon-reload
sudo systemctl enable elia-bot
sudo systemctl start elia-bot
Controleer de status:

bash
Copy code
sudo systemctl status elia-bot

# Of volg de logs
journalctl -u elia-bot -f
