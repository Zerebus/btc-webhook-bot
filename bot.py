
import os
import asyncio
import telegram
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import logging

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    logging.info(f"Received webhook data: {data}")

    test_mode = data.get("test", False)

    if test_mode:
        # Fancy Telegram message format
        signal = data.get("signal", "UNKNOWN").upper()
        pair = data.get("pair", "N/A")
        risk = data.get("risk", "N/A")
        sl_pct = data.get("sl_pct", "N/A")
        tp1_pct = data.get("tp1_pct", "N/A")
        tp2_pct = data.get("tp2_pct", "N/A")

        title = f"📈 {signal} SIGNAL (Test Mode Active)"
        message = f"""<b>{title}</b>

<b>Pair:</b> {pair}
<b>Risk:</b> {risk}
<b>SL:</b> {sl_pct}%
<b>TP1:</b> {tp1_pct}%
<b>TP2:</b> {tp2_pct}%"""

        asyncio.run(send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode="HTML"))
        logging.info("Test alert sent to Telegram.")
        return jsonify({"status": "Test alert sent"})
    else:
        logging.info("Live trading mode active.")
        return jsonify({"status": "Live trading logic would be here"})

async def send_message(chat_id, text, parse_mode="HTML"):
    try:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
    except Exception as e:
        logging.error(f"Telegram error: {e}")

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=10000)
