import os
import logging
import asyncio
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from telegram import Bot

# Load environment variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID"))  # Cast to int

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

async def send_telegram_message(message: str):
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.info("✅ Telegram message sent successfully.")
    except Exception as e:
        logging.error(f"❌ Failed to send Telegram message: {e}")

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    logging.info(f"Received webhook data: {data}")

    if data.get("test") is True:
        message = "🚀 Test alert from your webhook bot!"
        asyncio.run(send_telegram_message(message))
        return jsonify({"status": "Test alert sent"}), 200

    return jsonify({"status": "No action taken"}), 200

if __name__ == "__main__":
    app.run(debug=False, port=5000, host="0.0.0.0")
