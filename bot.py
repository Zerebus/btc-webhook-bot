import os
import json
import asyncio
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from telegram import Bot
import aiohttp

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

bot = Bot(token=TELEGRAM_BOT_TOKEN)
session = aiohttp.ClientSession()  # Shared session

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    logging.info(f"Received webhook data: {data}")

    signal = data.get("signal")
    pair = data.get("pair")
    sl_pct = data.get("sl_pct")
    tp1_pct = data.get("tp1_pct")
    tp2_pct = data.get("tp2_pct")
    risk = data.get("risk")
    test_mode = data.get("test", False)

    if test_mode:
        title = "📈 LONG SIGNAL (Test Mode Active)" if signal == "LONG" else "📉 SHORT SIGNAL (Test Mode Active)"
        message = (
            f"<b>{title}</b>\n"
            f"<b>Pair:</b> {pair}\n"
            f"<b>Risk:</b> {risk}\n"
            f"<b>SL:</b> {sl_pct}%\n"
            f"<b>TP1:</b> {tp1_pct}%\n"
            f"<b>TP2:</b> {tp2_pct}%"
        )
    else:
        message = "🚀 Test alert from your webhook bot!"

    try:
        asyncio.run(send_message(TELEGRAM_CHAT_ID, message))
        logging.info("Telegram alert sent successfully.")
    except Exception as e:
        logging.error(f"Telegram error: {e}")

    return jsonify({"status": "ok"})

async def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }
    async with session.post(url, json=payload) as response:
        return await response.text()

@app.before_first_request
def setup_event_loop():
    global loop
    loop = asyncio.get_event_loop()

@app.route("/")
def home():
    return "Webhook bot is running."

@app.teardown_appcontext
def cleanup(exception=None):
    if session and not session.closed:
        loop.run_until_complete(session.close())

if __name__ == "__main__":
    app.run(debug=False, port=5000)