from flask import Flask, request
import os
import telegram
import logging

# Telegram Bot Config
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

# Logging
logging.basicConfig(level=logging.INFO)

# Flask App
app = Flask(__name__)

@app.route('/')
def home():
    return '✅ Bot is running!'

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    logging.info(f"📩 Received webhook data: {data}")

    try:
        signal = data.get("signal")
        pair = data.get("pair")
        sl_pct = data.get("sl_pct")
        tp1_pct = data.get("tp1_pct")
        tp2_pct = data.get("tp2_pct")
        risk = data.get("risk")
        test = data.get("test")

        message = f"📉 {signal} SIGNAL {'(Test Mode Active)' if test else ''}\n" + \
                  f"<b>Pair:</b> {pair}\n" + \
                  f"<b>Risk:</b> {risk}\n" + \
                  f"<b>SL:</b> {sl_pct}%\n" + \
                  f"<b>TP1:</b> {tp1_pct}%\n" + \
                  f"<b>TP2:</b> {tp2_pct}%"

        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode=telegram.constants.ParseMode.HTML)
        logging.info("✅ Telegram alert sent successfully.")
        return '', 200

    except Exception as e:
        logging.error(f"❌ Failed to send Telegram alert: {e}")
        return 'Error', 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
