
from flask import Flask, request
import json
import logging
import os
import requests
from telegram import Bot

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = Bot(token=TELEGRAM_BOT_TOKEN)

@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()
    logging.info(f"Received webhook data: {json.dumps(data)}")

    if data.get("test"):
        msg = format_telegram_message(data, test_mode=True)
    else:
        msg = format_telegram_message(data, test_mode=False)

    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg, parse_mode="HTML")
        logging.info("Telegram alert sent successfully.")
    except Exception as e:
        logging.error(f"Failed to send Telegram message: {e}")

    return "", 200

def format_telegram_message(data, test_mode=False):
    prefix = "📈 <b>LONG SIGNAL</b>" if data["signal"] == "LONG" else "📉 <b>SHORT SIGNAL</b>"
    if test_mode:
        prefix += " (Test Mode Active)"
    return (
        f"{prefix}\n"
        f"<b>Pair:</b> {data['pair']}\n"
        f"<b>Risk:</b> {data['risk']}\n"
        f"<b>SL:</b> {data['sl_pct']}%\n"
        f"<b>TP1:</b> {data['tp1_pct']}%\n"
        f"<b>TP2:</b> {data['tp2_pct']}%"
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
