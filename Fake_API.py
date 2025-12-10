from flask import Flask, request, jsonify
import datetime
import random 

app = Flask(__name__)

# Globale instellingen
current_value = 0
random_mode = False 

@app.route("/setvalue")
def set_value():
    """Stel handmatig een vaste waarde in (en zet random uit)."""
    global current_value, random_mode
    try:
        current_value = float(request.args.get("value", current_value))
        random_mode = False  # Handmatig iets instellen stopt de random generator
    except ValueError:
        pass
    return f"✅ Handmatig: Waarde is {current_value} (Random modus gestopt)"

@app.route("/random")
def toggle_random():
    """Zet de random generator aan of uit."""
    global random_mode
    enable = request.args.get("enable", "true").lower()
    
    if enable == "true" or enable == "1":
        random_mode = True
        return "🎲 Random modus AAN: Prijs verandert elke check."
    else:
        random_mode = False
        return f"🛑 Random modus UIT: Prijs blijft staan op {current_value}."

@app.route("/testdata")
def testdata():
    """Dit is de link die de bot aanroept."""
    global current_value
    
    if random_mode:
        # Verzin een nieuwe prijs tussen -100 en 500
        current_value = round(random.uniform(-100, 500), 2)

    return jsonify({
        "results": [{
            "imbalanceprice": current_value,
            "datetime": datetime.datetime.now().isoformat()
        }]
    })

if __name__ == "__main__":
    print("🚀 Fake API gestart op poort 5000")
    app.run(port=5000)

'''
==========================================
HOW TO USE THIS FAKE API
==========================================
1. Run this file: python3 Fake_API.py

2. Update your .env file: ELIA_API_URL=http://localhost:5000/testdata

3. CONTROLS (Open in browser):
  - Set specific price (e.g. 0):
    http://localhost:5000/setvalue?value=0
  - Enable RANDOM mode (Price changes every 15s):
    http://localhost:5000/random?enable=true
  - Disable RANDOM mode:
    http://localhost:5000/random?enable=false
'''