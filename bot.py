
import os
import json
import logging
import asyncio
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError

load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(token=TELEGRAM_BOT_TOKEN)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    logging.info(f"Received webhook data: {data}")

    if data.get("test"):
        message = "🚀 Test alert from your webhook bot!"
        asyncio.run(send_telegram_message(TELEGRAM_CHAT_ID, message))
        return jsonify({"status": "Test alert sent"})

    return jsonify({"status": "No test flag"})


async def send_telegram_message(chat_id, text):
    try:
        await bot.send_message(chat_id=chat_id, text=text)
    except TelegramError as e:
        logging.error(f"Telegram error: {e}")

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=10000)
