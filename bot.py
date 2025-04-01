import os
import logging
import json
import aiohttp
import asyncio
import nest_asyncio  # <-- NEW
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()
nest_asyncio.apply()  # <-- NEW

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Shared aiohttp session
session = None

@app.before_first_request
def create_session():
    global session
    session = aiohttp.ClientSession()

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    logging.info(f"Received webhook data: {data}")

    # Required fields
    required_fields = ["signal", "pair", "sl_pct", "tp1_pct", "tp2_pct", "risk"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing fields in webhook data"}), 400

    is_test = data.get("test", False)

    # Format Telegram message
    emoji = "\ud83d\udcc8" if data["signal"].upper() == "LONG" else "\ud83d\udcc9"
    title = f"<b>{emoji} {data['signal'].upper()} SIGNAL {'(Test Mode Active)' if is_test else ''}</b>"
    message = f"""
{title}

<b><u>Pair:</u></b> {data['pair']}
<b><u>Risk:</u></b> {data['risk']}
<b><u>SL:</u></b> {data['sl_pct']}%
<b><u>TP1:</u></b> {data['tp1_pct']}%
<b><u>TP2:</u></b> {data['tp2_pct']}%
"""

    loop = asyncio.get_event_loop()

    if is_test:
        logging.info("Test mode active. Sending Telegram alert only.")
        loop.create_task(send_message(TELEGRAM_CHAT_ID, message))
        return jsonify({"status": "Test alert sent to Telegram."}), 200

    # Real trade logic would go here (currently omitted)
    logging.info("Live mode: No trade logic active in this test.")
    loop.create_task(send_message(TELEGRAM_CHAT_ID, message))
    return jsonify({"status": "Live alert (trade logic pending) sent to Telegram."}), 200

async def send_message(chat_id, text):
    global session
    if session is None:
        session = aiohttp.ClientSession()

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        async with session.post(url, json=payload) as resp:
            if resp.status != 200:
                logging.error(f"Telegram API error: {resp.status} - {await resp.text()}")
            else:
                logging.info("Telegram alert sent successfully.")
    except Exception as e:
        logging.error(f"Telegram error: {e}")

if __name__ == "__main__":
    app.run(debug=False, port=5000)


