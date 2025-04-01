import os
import logging
from flask import Flask, request, jsonify
from telegram import Bot
from telegram.error import TelegramError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Initialize Flask and Telegram Bot
app = Flask(__name__)
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Configure logging
logging.basicConfig(level=logging.INFO)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    logging.info(f"Received webhook data: {data}")

    if data.get("test") is True:
        try:
            message = "🔥 This is a test alert from your trading bot."
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
            logging.info("Test alert sent to Telegram.")
            return jsonify({"status": "Test alert sent"})
        except TelegramError as e:
            logging.error(f"Telegram error: {e}")
            return jsonify({"error": str(e)}), 500

    return jsonify({"status": "Webhook received"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)