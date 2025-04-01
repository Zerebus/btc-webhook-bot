import os
import json
import logging
import asyncio
import telegram
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

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
    test = data.get("test", False)

    message = f"📈 {signal} SIGNAL"
    if test:
        message += " (Test Mode Active)"
    message += f"\nPair: {pair}\nRisk: {risk}\nSL: {sl_pct}%\nTP1: {tp1_pct}%\nTP2: {tp2_pct}%"

    try:
        asyncio.run(bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message))
        logging.info("Telegram alert sent successfully.")
    except Exception as e:
        logging.error(f"Telegram error: {e}")

    return {"status": "ok"}

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=10000)