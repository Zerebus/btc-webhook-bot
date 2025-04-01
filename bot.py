import os
import json
import logging
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

def send_telegram_message(message: str):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            logging.error(f"Failed to send Telegram message: {response.text}")
    except Exception as e:
        logging.error(f"Telegram error: {e}")

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    logging.info(f"Received webhook data: {data}")

    try:
        signal = data.get("signal", "").upper()
        pair = data.get("pair", "BTC-USDT")
        sl_pct = data.get("sl_pct", 1)
        tp1_pct = data.get("tp1_pct", 2)
        tp2_pct = data.get("tp2_pct", 4)
        risk = data.get("risk", "1%")
        test = data.get("test", False)

        if test:
            send_telegram_message("🚀 Test alert from your webhook bot!")
            return jsonify({"status": "Test alert sent to Telegram."})

        message = f"📥 *{signal} SIGNAL*
Pair: {pair}
Risk: {risk}
TP1: {tp1_pct}% | TP2: {tp2_pct}% | SL: {sl_pct}%"
        send_telegram_message(message)
        return jsonify({"status": "Live trade alert sent to Telegram."})

    except Exception as e:
        logging.error(f"Webhook processing error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=3000)
