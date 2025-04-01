
import os
import requests

def send_telegram_message(message):
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Missing Telegram credentials in environment variables.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print(f"Telegram error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

from flask import Flask, request, jsonify
import requests
import time
import hmac
import hashlib
import json
import os
import datetime

app = Flask(__name__)

API_KEY = os.getenv("OKX_API_KEY")
SECRET_KEY = os.getenv("OKX_SECRET_KEY")
PASSPHRASE = os.getenv("OKX_PASSPHRASE")
BASE_URL = "https://www.okx.com"

def get_timestamp():
    return datetime.datetime.utcnow().isoformat("T", "milliseconds") + "Z"

def generate_signature(timestamp, method, path, body):
    prehash = f"{timestamp}{method.upper()}{path}{body}"
    return hmac.new(SECRET_KEY.encode(), prehash.encode(), hashlib.sha256).hexdigest()

def place_order(signal, pair, sl_pct, tp1_pct, tp2_pct, risk, test):
    timestamp = get_timestamp()
    path = "/api/v5/trade/order"
    method = "POST"

    side = "buy" if signal == "LONG" else "sell"
    size = "1"  # In production, this will be calculated based on risk management

    body = {
        "instId": pair,
        "tdMode": "cross",
        "side": side,
        "ordType": "market",
        "sz": size,
        "tag": "ai-sniper-2.6"
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

    if test:
        print("DEBUG BODY:", body_json)
        print("DEBUG HEADERS:", headers)
        return {"debug": True, "body": body, "headers": headers}

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
        test = data.get("test", False)

        result = place_order(signal, pair, sl_pct, tp1_pct, tp2_pct, risk, test)
        return jsonify({"status": "order sent", "okx_response": result})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/", methods=["GET"])
def home():
    return "AI Sniper 2.6 Webhook Bot is live!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)


