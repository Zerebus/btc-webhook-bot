import os
import json
import logging
import asyncio
import aiohttp
from flask import Flask, request
from telegram import Bot
from telegram.constants import ParseMode
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
bot = Bot(token=TELEGRAM_BOT_TOKEN)
session = None  # will be initialized in before_serving

@app.before_serving
async def create_session():
    global session
    session = aiohttp.ClientSession()

@app.after_serving
async def close_session():
    await session.close()

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json
        logging.info("Received webhook data: %s", data)

        # Extract data safely
        signal = data.get("signal", "N/A")
        pair = data.get("pair", "N/A")
        sl_pct = data.get("sl_pct", "N/A")
        tp1_pct = data.get("tp1_pct", "N/A")
        tp2_pct = data.get("tp2_pct", "N/A")
        risk = data.get("risk", "N/A")
        test_mode = data.get("test", True)

        # Build fancy message
        title = f"\uD83D\uDCC8 <b>{signal} SIGNAL</b> {'<i>(Test Mode Active)</i>' if test_mode else ''}"
        details = f"""
<b>Pair:</b> {pair}
<b>Risk:</b> {risk}
<b>SL:</b> {sl_pct}
<b>TP1:</b> {tp1_pct}
<b>TP2:</b> {tp2_pct}
"""
        message = f"{title}\n{details}"

        asyncio.run(send_message(message))
        logging.info("Test alert sent to Telegram.")

        return {"status": "ok"}, 200

    except Exception as e:
        logging.exception("Webhook processing failed")
        return {"error": str(e)}, 500

async def send_message(text):
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode=ParseMode.HTML)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
