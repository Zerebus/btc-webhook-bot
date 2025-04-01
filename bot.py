from flask import Flask, request
import requests
import json
import os
import logging
from dotenv import load_dotenv
import hmac
import hashlib
import base64
import time
import httpx

# === Load Environment ===
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
OKX_API_KEY = os.getenv("OKX_API_KEY")
OKX_SECRET_KEY = os.getenv("OKX_SECRET_KEY")
OKX_PASSPHRASE = os.getenv("OKX_PASSPHRASE")

# === Flask App ===
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# === Send Telegram Alert ===
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, data=payload)
    except Exception as e:
        logging.error(f"Telegram Error: {e}")

# === OKX Signature ===
def okx_signature(timestamp, method, request_path, body):
    body = body if body else ""
    message = f"{timestamp}{method.upper()}{request_path}{body}"
    mac = hmac.new(bytes(OKX_SECRET_KEY, encoding='utf8'), bytes(message, encoding='utf-8'), digestmod=hashlib.sha256)
    d = mac.digest()
    return base64.b64encode(d).decode()

# === Place Order ===
def place_order(signal, symbol, sl_pct, tp1_pct, tp2_pct):
    side = "buy" if signal == "LONG" else "sell"
    positionSide = "long" if signal == "LONG" else "short"
    leverage = 5  # Adjustable

    url = "https://www.okx.com/api/v5/trade/order"
    timestamp = str(time.time())
    headers = {
        "Content-Type": "application/json",
        "OK-ACCESS-KEY": OKX_API_KEY,
        "OK-ACCESS-SIGN": okx_signature(timestamp, "POST", "/api/v5/trade/order", ""),
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": OKX_PASSPHRASE,
    }
    body = {
        "instId": symbol,
        "tdMode": "cross",
        "side": side,
        "ordType": "market",
        "sz": "auto",  # Placeholder for auto size logic
        "posSide": positionSide
    }
    try:
        response = httpx.post(url, headers=headers, json=body)
        logging.info(f"OKX Response: {response.text}")
        send_telegram(f"✅ <b>Order Sent</b>\n<b>Type:</b> {signal}\n<b>Pair:</b> {symbol}\n<b>SL:</b> {sl_pct}%\n<b>TP1:</b> {tp1_pct}%\n<b>TP2:</b> {tp2_pct}%")
    except Exception as e:
        logging.error(f"OKX Order Error: {e}")
        send_telegram(f"⚠️ <b>Trade Failed</b>\nError: {e}")

# === Webhook Endpoint ===
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    logging.info(f"Webhook Data: {data}")
    
    try:
        signal = data.get("signal")
        symbol = data.get("pair")
        sl_pct = data.get("sl_pct")
        tp1_pct = data.get("tp1_pct")
        tp2_pct = data.get("tp2_pct")
        test = data.get("test")

        formatted = f"📡 <b>{'TEST' if test else 'LIVE'} SIGNAL</b>\n" \
                   f"<b>Signal:</b> {signal}\n<b>Pair:</b> {symbol}\n<b>SL:</b> {sl_pct}%\n<b>TP1:</b> {tp1_pct}%\n<b>TP2:</b> {tp2_pct}%"
        send_telegram(formatted)

        if not test:
            place_order(signal, symbol, sl_pct, tp1_pct, tp2_pct)

        return {"status": "ok"}, 200
    except Exception as e:
        logging.error(f"Webhook Error: {e}")
        return {"status": "error", "message": str(e)}, 500

# === Main Entrypoint ===
if __name__ == "__main__":
    app.run(debug=True)


