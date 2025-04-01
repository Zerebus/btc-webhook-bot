
import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from telegram import Bot, constants
import asyncio

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

app = Flask(__name__)
bot = Bot(token=TELEGRAM_BOT_TOKEN)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Received webhook data:", data)

    # Construct a message from the alert data
    msg = (
        f"📉 *{data['signal']} SIGNAL*\n\n"
        f"*Pair:* {data['pair']}\n"
        f"*Risk:* {data['risk']}\n"
        f"*SL:* {data['sl_pct']}%\n"
        f"*TP1:* {data['tp1_pct']}%\n"
        f"*TP2:* {data['tp2_pct']}%\n"
    )

    if data.get("test"):
        msg = "🧪 *TEST MODE ACTIVE*\n\n" + msg

    # Send message to Telegram asynchronously
    asyncio.run(send_telegram_message(msg))
    print("✅ Telegram alert sent successfully.")
    return jsonify({"status": "ok"}), 200

async def send_telegram_message(message):
    await bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message,
        parse_mode=constants.ParseMode.MARKDOWN
    )

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=10000)
