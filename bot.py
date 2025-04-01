import os
import logging
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Telegram alert sender
def send_telegram_alert(message):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown"
            }
            response = requests.post(url, json=payload)
            logger.info(f"Telegram response: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
    else:
        logger.warning("Telegram credentials are not set!")

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    logger.info(f"Received webhook: {data}")

    if data.get("test"):
        logger.info("* Test Alert Triggered *")
        send_telegram_alert("🚀 *Test Alert Received!* \nThis confirms Telegram integration is working!")
        return jsonify({"status": "Test alert sent"})

    # You can add real trade processing logic below
    signal = data.get("signal")
    pair = data.get("pair")
    risk = data.get("risk")

    msg = f"📈 *New Trade Signal*\nSignal: `{signal}`\nPair: `{pair}`\nRisk: `{risk}`"
    send_telegram_alert(msg)

    return jsonify({"status": "Trade alert processed"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
