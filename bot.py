from flask import Flask, request, jsonify
import requests
import time
import hmac
import hashlib
import json
import os

app = Flask(__name__)

API_KEY = os.getenv("OKX_API_KEY")
SECRET_KEY = os.getenv("OKX_SECRET_KEY")
PASSPHRASE = os.getenv("OKX_PASSPHRASE")
BASE_URL = "https://www.okx.com"

def get_timestamp():
    return str(int(time.time() * 1000))

def generate_signature(timestamp, method, path, body):
    prehash = f"{timestamp}{method.upper()}{path}{body}"
    return hmac.new(SECRET_KEY.encode(), prehash.encode(), hashlib.sha256).hexdigest()

def place_order(signal, pair, sl_pct, tp1_pct, tp2_pct, risk):
    timestamp = get_timestamp()
    path = "/api/v5/trade/order"
    method = "POST"

    side = "buy" if signal == "LONG" else "sell"
    size = "1"

    body = {
        "instId": pair,
        "tdMode": "cross",
        "side": side,
        "ordType": "market",
        "sz": size,
        "tag": "webhook-bot"
    }

    body_json = json.dumps(body)
    signature = generate_signature(timestamp, method, path, body_json)

    headers = {
        "OK-ACCESS-KEY": API_KEY,
        "OK-ACCESS-SIGN": signature,
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": PASSPHRASE,
        "Content-Type": "application/json"
    }

    response = requests.post(f"{BASE_URL}{path}", headers=headers, data=body_json)
    return response.json()

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    try:
        signal = data["signal"]
        pair = data["pair"]
        sl_pct = float(data["sl_pct"])
        tp1_pct = float(data["tp1_pct"])
        tp2_pct = float(data["tp2_pct"])
        risk = data["risk"]

        result = place_order(signal, pair, sl_pct, tp1_pct, tp2_pct, risk)
        return jsonify({"status": "order sent", "okx_response": result})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/", methods=["GET"])
def home():
    return "Webhook Bot is live on Render!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)