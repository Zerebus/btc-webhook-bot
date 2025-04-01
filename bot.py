import os
import logging
from flask import Flask, request, jsonify
from telegram import Bot
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app and Telegram bot
app = Flask(__name__)
bot = Bot(token=TELEGRAM_BOT_TOKEN)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    logger.info(f"Received webhook: {data}")

    try:
        if data.get("test"):
            msg = "✅ Test alert received from your bot!"
        else:
            signal = data.get("signal")
            pair = data.get("pair")
            sl = data.get("sl_pct")
            tp1 = data.get("tp1_pct")
            tp2 = data.get("tp2_pct")
            risk = data.get("risk")

            msg = (
                f"🚨 *{signal.upper()} Signal*\n"
                f"Pair: `{pair}`\n"
                f"SL: `{sl}%`, TP1: `{tp1}%`, TP2: `{tp2}%`\n"
                f"Risk: `{risk}`"
            )

        if msg:
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg, parse_mode="Markdown")
            logger.info("Telegram message sent.")
            return jsonify({"status": "message sent"})
        else:
            logger.error("Message was None.")
            return jsonify({"status": "error", "reason": "message was None"}), 500

    except Exception as e:
        logger.exception("Failed to send Telegram message.")
        return jsonify({"status": "error", "reason": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=False)



