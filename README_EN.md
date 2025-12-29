# ⚡ Elia Imbalance Price Telegram Bot

An efficient Python script that continuously monitors the **imbalance prices** of the Belgian grid operator **Elia**. It instantly sends a **Telegram notification** when electricity prices are extremely high or low.

The script is optimized to run **24/7** on a Raspberry Pi or server and requires minimal system resources.

---

## 🧠 What does this script do?

* 📡 **Real-time Monitoring:** Checks the current imbalance price via the Elia API every 15 seconds.
* 📊 **Graphs:** Generates a visual graph of the day's price trend upon request.
* 📈 **Daily Statistics:** Continuously tracks the highest, lowest, and average price of the day.
* 🎨 **Clear Notifications:** Sends messages with **bold** prices and a compact layout optimized for mobile.
* 🛡️ **Anti-Spam:** Smart logic prevents "flapping" notifications if the price fluctuates around a threshold.
* 🔁 **Status Updates:** Automatically reports when the server (or script) has restarted.
* 💬 **Commands:**
    * `/price` - Receive the current price instantly.
    * `/vandaag` - View today's overview (Min / Max / Average).
    * `/grafiek` - Generate an image of today's price trend.
* 🔒 **Robust:** Keeps running during internet outages or API errors (auto-retry).

### 📊 Notification Thresholds:
* 🧊 **Extremely low:** < -500 €/MWh
* ❄️ **Very low:** < -150 €/MWh
* 🌟 **Negative:** < -50 €/MWh
* ✅ **Below zero:** < 0 €/MWh
* ⚠️ **Cheap:** < 50 €/MWh
* 🚨 **Very high:** > 400 €/MWh

---

## 🧩 Installation

### 1. Download the code
Clone this repository to your Raspberry Pi or computer:

```bash
git clone [https://github.com/WonterRobter/Onbalansprijs_telegram.git](https://github.com/WonterRobter/Onbalansprijs_telegram.git)
cd Onbalansprijs_telegram
```

### 2. Install requirements ("Ingredients")

This script needs a few tools (like `matplotlib` for charts). The `requirements.txt` file is the **shopping list**; install everything at once with this command:

```bash
sudo apt update
sudo apt install python3-pip -y
pip3 install -r requirements.txt
```

### 3. Configuration (.env)

The script needs a configuration file with your secret keys. Create a file named `.env` in the same folder:

```bash
nano .env
```

Paste the following lines and fill in your own details:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_CHAT_IDS=123456789,987654321
ELIA_API_URL=[https://api.elia.be/](https://api.elia.be/)...

```

**Where do I find this data?**

* `TELEGRAM_BOT_TOKEN`: Create a new bot via [@BotFather](https://t.me/BotFather) on Telegram.
* `TELEGRAM_CHAT_IDS`: Your personal ID. Get this from a bot like `@userinfobot`. You can add multiple IDs separated by a comma.
* `ELIA_API_URL`: The URL to the Elia Open Data API endpoint providing the `imbalanceprice`.

---

## 🧪 Testing with Fake API

Want to test specific scenarios (e.g., what happens at -100 or +500 euros) without waiting for the market? Use the included test tool.

1. **Start the Fake API:**
```bash
python3 Fake_API.py
```

2. **Temporarily modify your `.env` file:**
Comment out the real URL and add the local test URL:
```env
# ELIA_API_URL=[https://api.elia.be/](https://api.elia.be/)...
ELIA_API_URL=http://localhost:5000/testdata
```

3. **Start the bot in a new window:**
```bash
python3 raspberryonbalansprijs.py
```

4. **Control the price via your browser:**
Type the following link in your browser to set the price to **0**, for example:
* `http://localhost:5000/setvalue?value=0`

Change the number after `value=` to simulate other prices (e.g., `value=500` for an alarm). The bot will pick up the new value at the next check (every 15 sec).

⚠️ **Note:** Don't forget to change the URL in your `.env` file back to the real Elia link when you're done!

---

## 🔁 Automatic Startup (Raspberry Pi / Systemd)

Do you want the bot to run permanently, even after the Raspberry Pi reboots?

1. **Create a service file:**
```bash
sudo nano /etc/systemd/system/elia-bot.service

```


2. **Paste the following content:**
*(Adjust `/home/pi/Onbalansprijs_telegram/` if your folder is located elsewhere)*
```ini
[Unit]
Description=Elia Onbalansprijs Bot
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/Onbalansprijs_telegram/raspberryonbalansprijs.py
WorkingDirectory=/home/pi/Onbalansprijs_telegram
Restart=always
RestartSec=10
User=pi
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

3. **Enable the service:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable elia-bot
sudo systemctl start elia-bot
```

4. **Check the status:**
```bash
sudo systemctl status elia-bot
```
---

## 📦 Files in this Repo

* `raspberryonbalansprijs.py` - The main script (The engine of the program).
* `requirements.txt` - The list of required packages.
* `Fake_API.py` - A test tool to simulate extreme prices.
* `.env.example` - Example of what your .env file should look like.
* `.gitignore` - Ensures your .env file (containing passwords) isn't accidentally uploaded.

---

## 📜 License

This project is free to use (MIT License). Use it to your advantage to consume energy smartly!

Developed by **WonterRobter**.