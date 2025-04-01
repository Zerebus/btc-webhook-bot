
from flask import Flask, request, jsonify
import os
import logging
from dotenv import load_dotenv
load_dotenv("/etc/secrets/.env")  # Load secrets from Render's secret file

import requests
from dotenv import load_dotenv

# Load environment variables from Render secret file
load_dotenv("/etc/secrets/.env")

app = Flask(__name__)

# Telegram details
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram credentials missing!")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        r = requests.post(url, json=payload)
        if r.status_code != 200:
            print("❌ Telegram message failed:", r.text)
        else:
            print("✅ Telegram message sent!")
    except Exception as e:
        print(f"Telegram send error: {e}")

@app.route('/')
def home():
    return '✅ Bot is alive!'

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("Received webhook:", data)

    # Send test Telegram notification if `test = true`
    if data.get("test"):
        message = (
            "📣 *Test Alert Received!*

"
            f"Signal: `{data.get('signal')}`
"
            f"Pair: `{data.get('pair')}`
"
            f"TP1: `{data.get('tp1_pct')}%` | TP2: `{data.get('tp2_pct')}%`
"
            f"SL: `{data.get('sl_pct')}%` | Risk: `{data.get('risk')}`"
        )
        send_telegram_message(message)

    return jsonify({"status": "order sent", "debug": True})

if __name__ == '__main__':
    app.run(debug=False)
