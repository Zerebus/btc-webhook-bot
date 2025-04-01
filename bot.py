import os
import logging
from flask import Flask, request
from telegram import Bot, constants
import asyncio

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
bot = Bot(token=TELEGRAM_BOT_TOKEN)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    logging.info(f"Received webhook data: {data}")

    if not data:
        return "No data", 400

    signal = data.get("signal", "N/A")
    pair = data.get("pair", "N/A")
    sl_pct = data.get("sl_pct", "N/A")
    tp1_pct = data.get("tp1_pct", "N/A")
    tp2_pct = data.get("tp2_pct", "N/A")
    risk = data.get("risk", "N/A")
    test = data.get("test", False)

    emoji = "🧪" if test else "📉" if signal == "SHORT" else "📈"
    title = f"<b>{emoji} {signal} SIGNAL {'(Test Mode Active)' if test else ''}</b>"

    message = (
        f"{title}

"
        f"<b>Pair:</b> <code>{pair}</code>
"
        f"<b>Risk:</b> {risk}
"
        f"<b>SL:</b> {sl_pct}%
"
        f"<b>TP1:</b> {tp1_pct}%
"
        f"<b>TP2:</b> {tp2_pct}%"
    )

    asyncio.run(send_telegram(message))
    logging.info("✅ Telegram alert sent successfully.")
    return "OK", 200

async def send_telegram(message):
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode=constants.ParseMode.HTML)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)