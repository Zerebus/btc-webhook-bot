import os
import hmac
import json
import time
import base64
import hashlib
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Load secrets from environment
OKX_API_KEY = os.environ.get("OKX_API_KEY")
OKX_SECRET_KEY = os.environ.get("OKX_SECRET_KEY")
OKX_PASSPHRASE = os.environ.get("OKX_PASSPHRASE")
BASE_URL = "https://www.okx.com"

HEADERS = {
    "Content-Type": "application/json",
    "OK-ACCESS-KEY": OKX_API_KEY,
    "OK-ACCESS-PASSPHRASE": OKX_PASSPHRASE
}

def get_synced_timestamp():
    try:
        res = requests.get("https://worldtimeapi.org/api/timezone/Etc/UTC")
        if res.status_code == 200:
            utc_time = res.json()["unixtime"]
            return str(utc_time * 1000)
        else:
            return str(int(time.time() * 1000))
    except:
        return str(int(time.time() * 1000))

def generate_signature(timestamp, method, request_path, body=""):
    message = f"{timestamp}{method}{request_path}{body}"
    mac = hmac.new(bytes(OKX_SECRET_KEY, encoding='utf-8'),
                   bytes(message, encoding='utf-8'), hashlib.sha256)
    d = mac.digest()
    return base64.b64encode(d).decode()

def place_order(signal, pair, entry, sl, tp1, tp2, risk):
    timestamp = get_synced_timestamp()
    symbol = pair.replace("-", "/").upper()
    side = "buy" if signal == "LONG" else "sell"
    
    notional = 376 * float(risk.strip('%')) / 100
    size = round(notional / entry, 4)

    order = {
        "instId": pair,
        "tdMode": "cross",
        "side": side,
        "ordType": "market",
        "sz": str(size)
    }

    body = json.dumps(order)
    signature = generate_signature(timestamp, "POST", "/api/v5/trade/order", body)

    HEADERS.update({
        "OK-ACCESS-SIGN": signature,
        "OK-ACCESS-TIMESTAMP": timestamp
    })

    url = f"{BASE_URL}/api/v5/trade/order"
    res = requests.post(url, headers=HEADERS, data=body)
    return res.json()

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    try:
        response = place_order(
            data['signal'],
            data['pair'],
            float(data['entry']),
            float(data['sl']),
            float(data['tp1']),
            float(data['tp2']),
            data['risk']
        )
        return jsonify({"status": "Order sent", "okx_response": response})
    except Exception as e:
        return jsonify({"status": "Error", "message": str(e)})

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=10000)


