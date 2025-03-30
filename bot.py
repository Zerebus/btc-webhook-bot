import os
import json
import hmac
import time
import base64
import hashlib
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Load API credentials from environment
OKX_API_KEY = os.environ.get("OKX_API_KEY")
OKX_SECRET_KEY = os.environ.get("OKX_SECRET_KEY")
OKX_PASSPHRASE = os.environ.get("OKX_PASSPHRASE")

BASE_URL = "https://www.okx.com"

def get_server_timestamp():
    try:
        response = requests.get(f"{BASE_URL}/api/v5/public/time")
        return response.json()['data'][0]['ts']
    except Exception as e:
        print("Failed to fetch OKX server time:", e)
        return str(int(time.time() * 1000))

def generate_signature(timestamp, method, request_path, body=""):
    message = f"{timestamp}{method}{request_path}{body}"
    mac = hmac.new(bytes(OKX_SECRET_KEY, encoding='utf-8'), message.encode('utf-8'), digestmod=hashlib.sha256)
    d = mac.digest()
    return base64.b64encode(d).decode()

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    signal = data.get("signal")
    pair = data.get("pair")
    entry = float(data.get("entry"))
    sl = float(data.get("sl"))
    tp1 = float(data.get("tp1"))
    tp2 = float(data.get("tp2"))
    risk = data.get("risk")

    timestamp = get_server_timestamp()

    symbol = pair.upper()
    side = "buy" if signal.upper() == "LONG" else "sell"
    notional = 376 * float(risk.strip('%')) / 100
    size = round(notional / entry, 4)

    order = {
        "instId": symbol,
        "tdMode": "cross",
        "side": side,
        "ordType": "market",
        "sz": str(size)
    }

    body = json.dumps(order)
    headers = {
        "Content-Type": "application/json",
        "OK-ACCESS-KEY": OKX_API_KEY,
        "OK-ACCESS-PASSPHRASE": OKX_PASSPHRASE,
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-SIGN": generate_signature(timestamp, "POST", "/api/v5/trade/order", body)
    }

    url = f"{BASE_URL}/api/v5/trade/order"
    res = requests.post(url, headers=headers, data=body)

    return jsonify({"okx_response": res.json(), "status": "Order sent"})

if __name__ == "__main__":
    app.run()


