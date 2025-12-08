from flask import Flask, request, jsonify
import datetime

app = Flask(__name__)

# Globale variabele om de huidige testwaarde te bewaren
current_value = 0

@app.route("/setvalue")
def set_value():
    global current_value
    try:
        current_value = float(request.args.get("value", current_value))
    except ValueError:
        pass
    return f"Testwaarde ingesteld op {current_value}"

@app.route("/testdata")
def testdata():
    return jsonify({
        "results": [{
            "imbalanceprice": current_value,
            "datetime": datetime.datetime.now().isoformat()
        }]
    })

if __name__ == "__main__":
    app.run(port=5000)


# http://localhost:5000/setvalue?value=0
# run this python file and use the above link to set the test value. change the value as needed.
# change your .env API url to http://localhost:5000/testdata to use the fake API.