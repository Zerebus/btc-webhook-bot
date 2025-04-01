import os
import logging
import traceback
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import asyncio
import aiohttp

load_dotenv()
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    logging.info("Received webhook data: %s", data)

    try:
        if data.get("test"):
            message = f"🚀 Test alert from your webhook bot!"
        else:
            signal = data.get("signal", "N/A")
            pair = data.get("pair", "N/A")
            risk = data.get("risk", "N/A")
            sl = data.get("sl_pct", "N/A")
            tp1 = data.get("tp1_pct", "N/A")
            tp2 = data.get("tp2_pct", "N/A")
            message = f"🔔 {signal} SIGNAL\nPair: {pair}\nRisk: {risk}\nSL: {sl}% | TP1: {tp1}% | TP2: {tp2}%"

        asyncio.run(send_telegram_alert(message))
        return jsonify({"status": "Alert sent"}), 200

    except Exception as e:
        logging.error("Error: %s", traceback.format_exc())
        return jsonify({"error": str(e)}), 500

async def send_telegram_alert(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    text = await response.text()
                    logging.error("Telegram error response: %s", text)
                else:
                    logging.info("Telegram alert sent successfully.")

    except Exception as e:
        logging.error("Telegram alert error: %s", traceback.format_exc())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)