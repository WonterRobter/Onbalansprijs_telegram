# ⚡ Elia Imbalance Price Telegram Bot

A Python script that automatically retrieves the **imbalance prices** from the Belgian grid operator **Elia** and sends **alerts via Telegram** when extreme price changes occur.  
The script is optimized to run **continuously on a Raspberry Pi**.

---

## 🧠 Features

- 📡 Fetches imbalance prices via the **Elia API**
- 🤖 Sends Telegram alerts when thresholds are crossed:
  - ⚠️ Below 50 €/MWh  
  - ✅ Below 0 €/MWh  
  - 🌟 Below -50 €/MWh  
  - ❄️ Very low (< -150 €/MWh)  
  - 🧊 Extremely low (< -500 €/MWh)  
  - 🚨 Very high (> 400 €/MWh)
- 🔁 Reports when the server or Raspberry Pi restarts
- 💬 Responds to the Telegram command `/price` with the current price
- 🔒 Fault-tolerant thanks to retries, logging, and backoff logic
- 🗂️ Modular design: separate files for API, Telegram, price logic, and monitoring

---

## 📂 Project Structure

```
Onbalansprijs_telegram/
├── onbalansprijs/
│   ├── __init__.py
│   ├── elia_api.py          # API-calls naar Elia
│   ├── telegram_bot.py      # Telegram berichten sturen/ontvangen
│   ├── prijs_logica.py      # Logica rond prijsstatus en meldingen
│   ├── prijs_monitor.py     # Loops en threads voor prijscontrole & monitoring
│   └── logging_helpers.py   # Logging setup en gedeelde sessie
├── configuratie.py          # Configuratie en environment variabelen
├── hoofdprogramma.py        # Startpunt van de applicatie
├── vereisten.txt            # Dependencies
└── .env.example             # Voorbeeld van vereiste variabelen
```

---

## 🧩 Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/WonterRobter/ImbalancePrice_Telegram.git
   cd ImbalancePrice_Telegram
   ```

2. Install requirements:

   ```bash
   sudo apt update
   sudo apt install python3-pip -y
   pip install -r requirements.txt
   ```

3. ⚙️ Configuration  
   Create a `.env` file in the root directory with the following content:

   ```env
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_CHAT_IDS=123456789,987654321
   ELIA_API_URL=https://api.elia.be/...   # The endpoint you use
   LOG_LEVEL=INFO
   ```

   **Explanation:**
   - `TELEGRAM_BOT_TOKEN` → Obtained via [@BotFather](https://t.me/BotFather)  
   - `TELEGRAM_CHAT_IDS` → Comma-separated list of Telegram chat IDs to receive alerts  
   - `ELIA_API_URL` → API endpoint for imbalance prices (Elia or your test API)  
   - `LOG_LEVEL` → Optional, default `INFO`  

   ⚠️ Don’t forget to add `.env` to your `.gitignore` so sensitive data isn’t uploaded to GitHub.

4. 🚀 Run the bot:

   ```bash
   python3 main.py
   ```

   The bot runs continuously, checking the current price every ~15 seconds.  
   It sends alerts when thresholds are crossed.

---

## 🔁 Auto-start with systemd (Raspberry Pi)

You can configure the bot to start automatically after each reboot using a systemd service:

1. Create a service file:

   ```bash
   sudo nano /etc/systemd/system/elia-bot.service
   ```

2. Add the following content:

   ```ini
   [Unit]
   Description=Telegram Bot Service
   After=network-online.target
   Wants=network-online.target

   [Service]
   ExecStart=/usr/bin/python3 /home/pi/ImbalancePrice_Telegram/main.py
   WorkingDirectory=/home/pi/ImbalancePrice_Telegram
   Restart=always
   RestartSec=5
   User=pi
   Environment=PYTHONUNBUFFERED=1

   [Install]
   WantedBy=multi-user.target
   ```

3. Enable the service:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable elia-bot
   sudo systemctl start elia-bot
   ```

4. Check the status:

   ```bash
   sudo systemctl status elia-bot
   ```

   **Or follow logs live:**

   ```bash
   journalctl -u elia-bot -f
   ```

---

## 📦 Requirements

Create a file named `requirements.txt` and add:

```
requests
python-dotenv
pytz
```

---

## 🚫 .gitignore

Add a `.gitignore` file to exclude sensitive or unnecessary files:

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

# OS files
.DS_Store
Thumbs.db
```

---

## 📊 Example Output in Telegram

When price drops below 0 €/MWh:
```
✅ Imbalance price below 0 : -12 €/MWh
🕒 Time: 14:30
```

When price rises above 400 €/MWh:
```
🚨 VERY HIGH imbalance price: 425 €/MWh
🕒 Time: 18:45
```

When the server reboots:
```
🔄 Server restarted!: 35 €/MWh
🕒 Time: 09:15
```

---

## ❓ FAQ

**What if the API is unreachable?**  
The bot retries with backoff logic. Errors are logged.

**Can I use multiple chat IDs?**  
Yes, provide them comma-separated in `TELEGRAM_CHAT_IDS`.

**Can I test without the real Elia API?**  
Yes, use the included fake API (`fake_api_dynamic.py`) and set `ELIA_API_URL=http://localhost:5000/testdata`.

**How often is the price checked?**  
Every 15 seconds (configurable in the code).

---

## 📜 License

This project is licensed under the [MIT License](./LICENSE).  
Free to use and adapt — please credit the original author.

---

## 💡 Credits

Developed by **Wouter**  
🧠 Built for **energy enthusiasts** who want real-time insight into Belgian imbalance prices.