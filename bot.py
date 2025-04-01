import os
import json
import asyncio
from flask import Flask, request, jsonify
import aiohttp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Global aiohttp session
session = None

# Telegram sending logic
async def send_telegram_message(message: str):
    global session
    if session is None:
        session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=10))

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("Missing Telegram credentials.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}

    try:
        async with session.post(url, json=payload, timeout=10) as resp:
            if resp.status != 200:
                print(f"Failed to send Telegram message: {resp.status}")
    except asyncio.TimeoutError:
        print("Telegram send timeout.")
    except Exception as e:
        print(f"Telegram send error: {e}")

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print("Received webhook data:", data)

    signal = data.get("signal")
    pair = data.get("pair")
    sl_pct = data.get("sl_pct")
    tp1_pct = data.get("tp1_pct")
    tp2_pct = data.get("tp2_pct")
    risk = data.get("risk")
    test = data.get("test", False)

    alert_msg = f"""
🚀 Trade Alert
Pair: {pair}
Signal: {signal}
Risk: {risk}
SL: {sl_pct}%
TP1: {tp1_pct}%
TP2: {tp2_pct}%
"""

    if test:
        alert_msg = "🚀 Test alert from your webhook bot!"

    asyncio.run(send_telegram_message(alert_msg))
    return jsonify({"status": "ok", "message": "Alert processed"})

# Cleanup
import atexit

@atexit.register
def shutdown():
    global session
    if session and not session.closed:
        asyncio.run(session.close())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
