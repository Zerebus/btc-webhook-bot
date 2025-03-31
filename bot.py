import json
import hmac
import time
import hashlib
import requests
from flask import Flask, request, jsonify
from datetime import datetime
import os

app = Flask(__name__)

# Load API credentials from environment variables
API_KEY = os.getenv("OKX_API_KEY")
SECRET_KEY = os.getenv("OKX_SECRET_KEY")
PASSPHRASE = os.getenv("OKX_PASSPHRASE")
BASE_URL = "https://www.okx.com"

# Get timestamp from OKX or fallback to system time
def get_okx_timestamp():
    try:
        res = requests.get("https://www.okx.com/api/v5/public/time", timeout=5)
        return str(res.json()['data'][0]['ts'])
    except Exception as e:
        print("Error syncing timestamp from OKX:", e)
        return str(int(time.time() * 1000))

# Sign the request
def sign_request(timestamp, method, request_path, body):
    message = timestamp + method + request_path + body
    mac = hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256)
    return mac.hexdigest()

# Place order
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print("Received webhook:", data)

    signal = data.get("signal")
    pair = data.get("pair")
    sl_pct = float(data.get("sl_pct"))
    tp1_pct = float(data.get("tp1_pct"))
    tp2_pct = float(data.get("tp2_pct"))
    risk = data.get("risk", "1%")
    test = data.get("test", False)

    # Dummy price (replace with real-time fetch logic)
    current_price = 82000
    
    direction = 1 if signal.upper() == "LONG" else -1

    entry = current_price
    sl = round(entry - direction * (entry * sl_pct / 100), 2)
    tp1 = round(entry + direction * (entry * tp1_pct / 100), 2)
    tp2 = round(entry + direction * (entry * tp2_pct / 100), 2)

    print(f"Entry: {entry}, SL: {sl}, TP1: {tp1}, TP2: {tp2}")

    response = place_order(signal, pair, entry, sl, tp1, tp2, risk, test)
    return jsonify({"okx_response": response.text, "status": "Order sent"})

def place_order(signal, pair, entry, sl, tp1, tp2, risk, test=False):
    path = "/api/v5/trade/order"
    method = "POST"
    timestamp = get_okx_timestamp()

    side = "buy" if signal.upper() == "LONG" else "sell"

    body_json = {
        "instId": pair,
        "tdMode": "cross",
        "side": side,
        "ordType": "market",
        "sz": "1"
    }
    
    body = json.dumps(body_json)
    sign = sign_request(timestamp, method, path, body)

    headers = {
        "OK-ACCESS-KEY": API_KEY,
        "OK-ACCESS-SIGN": sign,
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": PASSPHRASE,
        "Content-Type": "application/json"
    }

    response = requests.post(f"{BASE_URL}{path}", headers=headers, data=body)
    print("🚀 OKX Response:", response.text)
    return response

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=10000)
