import os
import json
import logging
import asyncio
import aiohttp
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from telegram import Bot

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Initialize Flask app and Telegram bot
app = Flask(__name__)
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Setup logging
logging.basicConfig(level=logging.INFO)

# Async message sender
async def send_message(chat_id, message, parse_mode="HTML"):
    try:
        async with aiohttp.ClientSession() as session:
            await bot.send_message(chat_id=chat_id, text=message, parse_mode=parse_mode)
    except Exception as e:
        logging.error(f"Telegram error: {e}")

# Webhook endpoint
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json
        logging.info(f"Received webhook data: {data}")

        signal = data.get("signal", "").upper()
        pair = data.get("pair", "")
        sl_pct = data.get("sl_pct", "")
        tp1_pct = data.get("tp1_pct", "")
        tp2_pct = data.get("tp2_pct", "")
        risk = data.get("risk", "")
        test = data.get("test", False)

        # Construct the formatted message
        if test:
            title = "🚀 <b>Test alert from your webhook bot!</b>"
            message = title
        else:
            title = f"📉 <b>{signal}</b> SIGNAL <i>(Test Mode Active)</i>"
            message = (
                f"{title}
"
                f"<b>Pair:</b> {pair}
"
                f"<b>Risk:</b> {risk}
"
                f"<b>SL:</b> {sl_pct}%
"
                f"<b>TP1:</b> {tp1_pct}%
"
                f"<b>TP2:</b> {tp2_pct}%"
            )

        asyncio.run(send_message(chat_id=TELEGRAM_CHAT_ID, message=message))
        return jsonify({"status": "Alert processed"}), 200

    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return jsonify({"error": str(e)}), 500

# Run the app
if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=10000)
