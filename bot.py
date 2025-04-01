
from flask import Flask, request
import json
import logging
import os
import requests
from telegram import Bot
import hmac
import hashlib
import base64
import time

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# === Environment Variables ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
OKX_API_KEY = os.getenv("OKX_API_KEY")
OKX_SECRET_KEY = os.getenv("OKX_SECRET_KEY")
OKX_PASSPHRASE = os.getenv("OKX_PASSPHRASE")
OKX_BASE_URL = "https://www.okx.com"

bot = Bot(token=TELEGRAM_BOT_TOKEN)

@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()
    logging.info(f"Received webhook data: {json.dumps(data)}")

    is_test = data.get("test", True)
    msg = format_telegram_message(data, test_mode=is_test)

    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg, parse_mode="HTML")
        logging.info("Telegram alert sent successfully.")
    except Exception as e:
        logging.error(f"Failed to send Telegram message: {e}")

    if not is_test:
        try:
            execute_okx_trade(data)
        except Exception as e:
            logging.error(f"❌ OKX trade failed: {e}")

    return "", 200

def format_telegram_message(data, test_mode=False):
    prefix = "📈 <b>LONG SIGNAL</b>" if data["signal"] == "LONG" else "📉 <b>SHORT SIGNAL</b>"
    if test_mode:
        prefix += " (Test Mode Active)"
    return (
        f"{prefix}\n"
        f"<b>Pair:</b> {data['pair']}\n"
        f"<b>Risk:</b> {data['risk']}\n"
        f"<b>SL:</b> {data['sl_pct']}%\n"
        f"<b>TP1:</b> {data['tp1_pct']}%\n"
        f"<b>TP2:</b> {data['tp2_pct']}%"
    )

# === OKX Trade Logic ===

def get_timestamp():
    return time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())

def sign_message(timestamp, method, request_path, body=""):
    message = f"{timestamp}{method}{request_path}{body}"
    mac = hmac.new(OKX_SECRET_KEY.encode(), message.encode(), hashlib.sha256)
    d = mac.digest()
    return base64.b64encode(d).decode()

def send_okx_request(method, endpoint, body=None):
    ts = get_timestamp()
    body_json = json.dumps(body) if body else ""
    headers = {
        "Content-Type": "application/json",
        "OK-ACCESS-KEY": OKX_API_KEY,
        "OK-ACCESS-SIGN": sign_message(ts, method, endpoint, body_json),
        "OK-ACCESS-TIMESTAMP": ts,
        "OK-ACCESS-PASSPHRASE": OKX_PASSPHRASE
    }
    url = OKX_BASE_URL + endpoint
    resp = requests.request(method, url, headers=headers, data=body_json)
    logging.info(f"OKX {method} {url} => {resp.status_code} {resp.text}")
    return resp.json()

def get_balance(currency="USDT"):
    result = send_okx_request("GET", f"/api/v5/account/balance?ccy={currency}")
    for item in result.get("data", [{}])[0].get("details", []):
        if item["ccy"] == currency:
            return float(item["availBal"])
    return 0.0

def execute_okx_trade(data):
    pair = data["pair"]
    signal = data["signal"]
    sl_pct = float(data["sl_pct"])
    tp_pct = float(data["tp2_pct"])  # use TP2 for main target
    risk_pct = float(data["risk"].strip('%'))

    balance = get_balance("USDT")
    risk_amount = balance * (risk_pct / 100)
    leverage = 3
    price = float(requests.get("https://api.okx.com/api/v5/market/ticker?instId=" + pair).json()["data"][0]["last"])
    qty = round((risk_amount * leverage) / price, 3)

    order_data = {
        "instId": pair,
        "tdMode": "cross",
        "side": "buy" if signal == "LONG" else "sell",
        "ordType": "market",
        "sz": str(qty)
    }
    send_okx_request("POST", "/api/v5/trade/order", order_data)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
