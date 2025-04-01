
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

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Initialize Telegram Bot
bot = Bot(token=TELEGRAM_BOT_TOKEN)

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        logging.info("Received webhook data: %s", data)

        if data.get("test"):
            message = "🚀 Test alert from your webhook bot!"
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
            logging.info("Test alert sent to Telegram.")
            return jsonify({"status": "Test alert sent"}), 200

        # Placeholder for trading logic (long/short)
        signal = data.get("signal")
        pair = data.get("pair")
        sl_pct = data.get("sl_pct")
        tp1_pct = data.get("tp1_pct")
        tp2_pct = data.get("tp2_pct")
        risk = data.get("risk")
        
        # Example Telegram update for live signals
        message = f"📈 Signal: {signal}\nPair: {pair}\nSL: {sl_pct}%\nTP1: {tp1_pct}%\nTP2: {tp2_pct}%\nRisk: {risk}"
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.info("Trade signal sent to Telegram.")

        return jsonify({"status": "Order received"}), 200

    except TelegramError as e:
        logging.error(f"Telegram error: {e}")
        return jsonify({"error": str(e)}), 500

    except Exception as e:
        logging.exception("Unhandled exception")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))  # Render-compatible
