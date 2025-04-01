from flask import Flask, request
import os
import json
from telegram import Bot
from telegram.constants import ParseMode

app = Flask(__name__)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(token=TELEGRAM_BOT_TOKEN)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print("✅ Received webhook data:", data)

    # Format message
    signal = data.get("signal", "UNKNOWN")
    pair = data.get("pair", "BTCUSDT.P")
    sl = data.get("sl_pct", 1)
    tp1 = data.get("tp1_pct", 1.25)
    tp2 = data.get("tp2_pct", 2.5)
    risk = data.get("risk", "1%")
    test = data.get("test", False)

    message = f"""
📉 <b>{'SHORT' if signal == 'SHORT' else 'LONG'} SIGNAL{' (Test Mode Active)' if test else ''}</b>

<b>Pair:</b> {pair}
<b>Risk:</b> {risk}
<b>SL:</b> {sl}%
<b>TP1:</b> {tp1}%
<b>TP2:</b> {tp2}%
"""

    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode=ParseMode.HTML)
    print("📨 Telegram alert sent successfully.")
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)