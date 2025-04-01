
import os
import json
import hmac
import hashlib
import time
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Load .env file from Render secret path
load_dotenv("/etc/secrets/.env")

app = Flask(__name__)

# --- ENV VARIABLES ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
OKX_API_KEY = os.getenv("OKX_API_KEY")
OKX_SECRET_KEY = os.getenv("OKX_SECRET_KEY")
OKX_PASSPHRASE = os.getenv("OKX_PASSPHRASE")
OKX_BASE_URL = "https://www.okx.com"

# --- TELEGRAM ---
def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Missing Telegram bot credentials.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        print("✅ Telegram response:", response.status_code, response.text)
    except Exception as e:
        print("Telegram error:", e)

# --- OKX Signature ---
def get_timestamp():
    return time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())

def generate_signature(timestamp, method, path, body):
    prehash = f"{timestamp}{method}{path}{body}"
    return hmac.new(OKX_SECRET_KEY.encode(), prehash.encode(), hashlib.sha256).hexdigest()

# --- OKX ORDER ---
def place_order(signal, pair, test=False):
    path = "/api/v5/trade/order"
    method = "POST"
    timestamp = get_timestamp()
    side = "buy" if signal == "LONG" else "sell"

    body_dict = {
        "instId": pair,
        "tdMode": "cross",
        "side": side,
        "ordType": "market",
        "sz": "1",
        "tag": "ai-sniper"
    }
    body = json.dumps(body_dict)
    sign = generate_signature(timestamp, method, path, body)

    headers = {
        "OK-ACCESS-KEY": OKX_API_KEY,
        "OK-ACCESS-SIGN": sign,
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": OKX_PASSPHRASE,
        "Content-Type": "application/json"
    }

    if test:
        print("[TEST MODE] Order payload:", body)
        send_telegram_message("🧪 *Test order triggered.*")
        return {"status": "test order sent"}

    response = requests.post(OKX_BASE_URL + path, headers=headers, data=body)
    print("OKX response:", response.status_code, response.text)
    return response.json()

# --- WEBHOOK ---
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("📩 Received webhook:", data)

    signal = data.get("signal")
    pair = data.get("pair", "BTC-USDT")
    test = data.get("test", False)

    message = f"🚨 *{signal} Signal Received* for `{pair}`"
    send_telegram_message(message)

    result = place_order(signal, pair, test=test)
    return jsonify(result)

@app.route("/", methods=["GET"])
def index():
    return "✅ AI Sniper bot is running."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
