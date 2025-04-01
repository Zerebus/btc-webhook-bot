import os
import logging
import json
import aiohttp
import asyncio
import nest_asyncio
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()
nest_asyncio.apply()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    logging.info(f"Received webhook data: {data}")

    required_fields = ["signal", "pair", "sl_pct", "tp1_pct", "tp2_pct", "risk"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing fields in webhook data"}), 400

    is_test = data.get("test", False)

    # Format Telegram message
    emoji = "📈" if data["signal"].upper() == "LONG" else "📉"
    title = f"<b>{emoji} {data['signal'].upper()} SIGNAL {'(Test Mode Active)' if is_test else ''}</b>"
    message = (
        f"{title}\n\n"
        f"<b><u>Pair:</u></b> {data['pair']}\n"
        f"<b><u>Risk:</u></b> {data['risk']}\n"
        f"<b><u>SL:</u></b> {data['sl_pct']}%\n"
        f"<b><u>TP1:</u></b> {data['tp1_pct']}%\n"
        f"<b><u>TP2:</u></b> {data['tp2_pct']}%\n"
    )

    if is_test:
        logging.info("✅ Test mode active. Sending Telegram alert only.")
    else:
        logging.info("🚀 Live mode active. Sending Telegram alert (trading logic not enabled).")

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(send_telegram_message(message))
        loop.close()
        return jsonify({"status": "Telegram alert sent"}), 200
    except Exception as e:
        logging.error(f"Telegram send error: {e}")
        return jsonify({"error": str(e)}), 500

async def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            if resp.status == 200:
                logging.info("✅ Telegram alert sent successfully.")
            else:
                logging.error(f"❌ Telegram error {resp.status}: {await resp.text()}")

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=10000)


