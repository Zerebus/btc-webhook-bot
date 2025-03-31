from flask import Flask, request, jsonify
import requests
import time
import hmac
import hashlib
import json
import os

app = Flask(__name__)

API_KEY = os.getenv("OKX_API_KEY")
API_SECRET = os.getenv("OKX_API_SECRET")
PASSPHRASE = os.getenv("OKX_PASSPHRASE")
BASE_URL = "https://www.okx.com"

@app.route("/")
def home():
    return "BTC Webhook Bot is running!"

def get_timestamp():
    return str(int(requests.get("https://www.okx.com/api/v5/public/time").json()["data"][0]["ts"]))

def sign(timestamp, method, request_path, body=""):
    message = f"{timestamp}{method}{request_path}{body}"
    return hmac.new(API_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()

def get_latest_price(pair):
    response = requests.get(f"{BASE_URL}/api/v5/market/ticker?instId={pair}")
    return float(response.json()["data"][0]["last"])

def place_order(signal, pair, entry, sl, tp1, tp2, risk, test=False):
    balance = 376.63
    risk_percent = float(risk.strip('%'))
    notional = max(5, balance * risk_percent / 100)
    size = round(notional / entry, 6)

    side = "buy" if signal.upper() == "LONG" else "sell"

    timestamp = get_timestamp()
    path = "/api/v5/trade/order"
    body = json.dumps({
        "instId": pair,
        "tdMode": "cross",
        "side": side,
        "ordType": "market",
        "sz": str(size)
    })

    headers = {
        "Content-Type": "application/json",
        "OK-ACCESS-KEY": API_KEY,
        "OK-ACCESS-SIGN": sign(timestamp, "POST", path, body),
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": PASSPHRASE,
        "x-simulated-trading": "0"
    }

    response = requests.post(f"{BASE_URL}{path}", headers=headers, data=body)
    print("🔁 OKX Response:", response.text)

    try:
        if not test:
            if not is_market_volatile_enough(pair):
                return {"status": "blocked", "reason": "low volatility"}

        okx_response = response.json() if hasattr(response, 'json') else response
        return jsonify({
            "status": "Order sent",
            "okx_response": okx_response,
            "raw_text": response.text
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    try:
        signal = data["signal"]
        pair = data["pair"]
        risk = data["risk"]

        if "sl_pct" in data and "tp1_pct" in data and "tp2_pct" in data:
            entry = get_latest_price(pair)
            sl = entry * (1 - float(data['sl_pct']) / 100) if signal.upper() == "LONG" else entry * (1 + float(data['sl_pct']) / 100)
            tp1 = entry * (1 + float(data['tp1_pct']) / 100) if signal.upper() == "LONG" else entry * (1 - float(data['tp1_pct']) / 100)
            tp2 = entry * (1 + float(data['tp2_pct']) / 100) if signal.upper() == "LONG" else entry * (1 - float(data['tp2_pct']) / 100)
        else:
            entry = float(data["entry"])
            sl = float(data["sl"])
            tp1 = float(data["tp1"])
            tp2 = float(data["tp2"])

        return place_order(signal, pair, entry, sl, tp1, tp2, risk, test=data.get("test", False))

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)