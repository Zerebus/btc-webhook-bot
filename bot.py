
import os
import json
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import telegram
import datetime
import requests

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Setup logging
logging.basicConfig(filename="trade_log.txt", level=logging.INFO, format="%(asctime)s - %(message)s")

# Telegram setup
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

# OKX placeholder functions
def place_okx_order(signal, pair, sl_pct, tp1_pct, tp2_pct, risk):
    # Simulated API call
    return {
        "status": "success",
        "order_id": "simulated_order_123",
        "entry_price": 68000.00,
        "stop_loss": 67320.00,
        "take_profit_1": 69360.00,
        "take_profit_2": 70720.00
    }

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    try:
        logging.info(f"Received webhook data: {data}")

        if data.get("test") == True:
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="🚀 Test alert from your webhook bot!")
            return jsonify({"status": "Test alert sent"})

        signal = data.get("signal")
        pair = data.get("pair", "BTC-USDT")
        sl_pct = float(data.get("sl_pct", 1))
        tp1_pct = float(data.get("tp1_pct", 2))
        tp2_pct = float(data.get("tp2_pct", 4))
        risk = data.get("risk", "1%")

        result = place_okx_order(signal, pair, sl_pct, tp1_pct, tp2_pct, risk)
        if result["status"] == "success":
            msg = (
                f"✅ Order Executed\n"
                f"Pair: {pair}\n"
                f"Signal: {signal}\n"
                f"Entry: {result['entry_price']}\n"
                f"SL: {result['stop_loss']}\n"
                f"TP1: {result['take_profit_1']}\n"
                f"TP2: {result['take_profit_2']}"
            )
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)
            logging.info("Trade executed and Telegram notified.")
            return jsonify({"status": "Order executed", "details": result})
        else:
            raise Exception("Failed to place order.")

    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        logging.error(error_msg)
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=error_msg)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=False)
