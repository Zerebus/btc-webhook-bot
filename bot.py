import os
import logging
from flask import Flask, request, jsonify
import telegram

app = Flask(__name__)

# Setup logging
logging.basicConfig(level=logging.INFO)

# Load Telegram credentials from environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Initialize the Telegram bot
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    logging.info(f"Received data: {data}")

    signal = data.get("signal", "").upper()
    pair = data.get("pair", "BTC-USDT")
    sl_pct = data.get("sl_pct", 1)
    tp1_pct = data.get("tp1_pct", 2)
    tp2_pct = data.get("tp2_pct", 4)
    risk = data.get("risk", "1%")
    test = data.get("test", False)

    if test:
        msg = "🚨 *Test Alert Received!*"
    elif signal == "LONG":
        msg = (
            f"🟢 *LONG Signal*\n"
            f"Pair: `{pair}`\n"
            f"Stop Loss: `{sl_pct}%`\n"
            f"Take Profit 1: `{tp1_pct}%`\n"
            f"Take Profit 2: `{tp2_pct}%`\n"
            f"Risk: `{risk}`"
        )
    elif signal == "SHORT":
        msg = (
            f"🔴 *SHORT Signal*\n"
            f"Pair: `{pair}`\n"
            f"Stop Loss: `{sl_pct}%`\n"
            f"Take Profit 1: `{tp1_pct}%`\n"
            f"Take Profit 2: `{tp2_pct}%`\n"
            f"Risk: `{risk}`"
        )
    else:
        return jsonify({"error": "Invalid signal"}), 400

    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg, parse_mode=telegram.constants.ParseMode.MARKDOWN)
        logging.info("Telegram message sent")
        return jsonify({"status": "Message sent"})
    except Exception as e:
        logging.error(f"Error sending Telegram message: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/")
def home():
    return "Bot is alive!"

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=3000)
