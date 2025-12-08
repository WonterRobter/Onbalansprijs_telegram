# ⚡ Elia Onbalansprijs Telegram Bot

Een efficiënt Python-script dat de **onbalansprijzen** van de Belgische netbeheerder **Elia** continu in de gaten houdt. Het stuurt direct een **melding via Telegram** wanneer de elektriciteitsprijzen extreem hoog of laag zijn.

Het script bestaat uit **één overzichtelijk bestand**, geoptimaliseerd om 24/7 te draaien op een Raspberry Pi of server.

---

## 🧠 Wat doet dit script?

* 📡 **Real-time Monitoring:** Checkt elke 15 seconden de actuele onbalansprijs via de Elia API.
* 🎨 **Duidelijke Meldingen:** Stuurt berichten met **dikgedrukte** prijzen en tijdstippen voor snelle leesbaarheid.
* 🛡️ **Anti-Spam:** Slimme logica voorkomt dat je elke minuut een bericht krijgt als de prijs rond een grens schommelt ("klapperen").
* 🔁 **Status Updates:** Meldt automatisch wanneer de server (of het script) opnieuw is opgestart.
* 💬 **Direct Opvragen:** Stuur het commando `/price` in Telegram om direct de huidige prijs te weten.
* 🔒 **Robuust:** Blijft draaien bij internetstoringen of API-fouten (auto-retry).

### 📊 Meldingen bij deze grenzen:
* 🧊 **Extreem laag:** < -500 €/MWh
* ❄️ **Zeer laag:** < -150 €/MWh
* 🌟 **Negatief:** < -50 €/MWh
* ✅ **Onder nul:** < 0 €/MWh
* ⚠️ **Goedkoop:** < 50 €/MWh
* 🚨 **Zeer hoog:** > 400 €/MWh

---

## 🧩 Installatie

### 1. Download de code
Clone deze repository naar je Raspberry Pi of computer:

```bash
git clone [https://github.com/WonterRobter/Onbalansprijs_telegram.git](https://github.com/WonterRobter/Onbalansprijs_telegram.git)
cd Onbalansprijs_telegram
````

### 2\. Installeer vereisten ("Ingrediënten")

Dit script heeft een paar hulpmiddelen nodig die niet standaard in Python zitten (zoals `requests` om met internet te praten).
Het bestand `requirements.txt` is het **boodschappenlijstje**; met dit commando installeer je alles in één keer:

```bash
sudo apt update
sudo apt install python3-pip -y
pip install -r requirements.txt
```

### 3\. Configuratie (.env)

Het script heeft een configuratiebestand nodig met jouw geheime sleutels.
Maak een bestand genaamd `.env` in dezelfde map:

```bash
nano .env
```

Plak hierin de volgende regels en vul je eigen gegevens in:

```env
TELEGRAM_BOT_TOKEN=jouw_bot_token_van_botfather
TELEGRAM_CHAT_IDS=123456789,987654321
ELIA_API_URL=[https://api.elia.be/](https://api.elia.be/)...
```

**Waar vind ik deze gegevens?**

  * `TELEGRAM_BOT_TOKEN`: Maak een nieuwe bot aan via [@BotFather](https://t.me/BotFather) op Telegram.
  * `TELEGRAM_CHAT_IDS`: Jouw persoonlijke ID. Vraag dit op bij een bot zoals `@userinfobot`. Je kunt meerdere ID's toevoegen gescheiden door een komma.
  * `ELIA_API_URL`: De URL naar de Elia Open Data API endpoint die de `imbalanceprice` levert.

-----

## 🧪 Testen met Fake API

Wil je specifieke scenario's testen (bijv. wat er gebeurt bij -100 of +500 euro) zonder te wachten op de markt? Gebruik de meegeleverde test-tool.

1.  **Start de Fake API:**
    ```bash
    python3 Fake_API.py
    ```
2.  **Pas je `.env` bestand tijdelijk aan:**
    Zet een hekje voor de echte URL en voeg de lokale test-URL toe:
    ```env
    # ELIA_API_URL=[https://api.elia.be/](https://api.elia.be/)...
    ELIA_API_URL=http://localhost:5000/testdata
    ```
3.  **Start de bot in een nieuw venster:**
    ```bash
    python3 main.py
    ```
4.  **Bestuur de prijs via je browser:**
    Typ de volgende link in je browser om de prijs naar bijvoorbeeld **0** te zetten:
    * `http://localhost:5000/setvalue?value=0`
    
    Verander het getal achter `value=` om andere prijzen te simuleren (bijv. `value=500` voor een alarm). De bot zal bij de volgende check (elke 15 sec) de nieuwe waarde oppikken.

⚠️ **Let op:** Vergeet niet de URL in je `.env` bestand terug te zetten naar de echte Elia-link als je klaar bent!

-----

## 🔁 Automatisch starten (Raspberry Pi / Systemd)

Wil je dat de bot altijd blijft draaien, ook als de Raspberry Pi opnieuw opstart?

1.  **Maak een service bestand:**

    ```bash
    sudo nano /etc/systemd/system/elia-bot.service
    ```

2.  **Plak de volgende inhoud erin:**
    *(Pas `/home/pi/Onbalansprijs_telegram/` aan als je map ergens anders staat)*

    ```ini
    [Unit]
    Description=Elia Onbalansprijs Bot
    After=network-online.target
    Wants=network-online.target

    [Service]
    ExecStart=/usr/bin/python3 /home/pi/Onbalansprijs_telegram/main.py
    WorkingDirectory=/home/pi/Onbalansprijs_telegram
    Restart=always
    RestartSec=10
    User=pi
    Environment=PYTHONUNBUFFERED=1

    [Install]
    WantedBy=multi-user.target
    ```

3.  **Activeer de service:**

    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable elia-bot
    sudo systemctl start elia-bot
    ```

4.  **Bekijk de status:**

    ```bash
    sudo systemctl status elia-bot
    ```

-----

## 📦 Bestanden in deze repo

  * `main.py` - Het hoofdscript (De motor van het programma).
  * `requirements.txt` - Het boodschappenlijstje met benodigde pakketten.
  * `Fake_API.py` - Een test-tool om extreme prijzen te simuleren.
  * `.env.example` - Voorbeeld van hoe je .env bestand eruit moet zien.
  * `.gitignore` - Zorgt dat je jouw .env bestand (met wachtwoorden) niet per ongeluk uploadt.

-----

## 📜 Licentie

Dit project is vrij te gebruiken (MIT License). Doe er je voordeel mee om slim energie te verbruiken\!

Ontwikkeld door **WonterRobter**.