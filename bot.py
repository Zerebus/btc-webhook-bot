import os
import time
import hmac
import hashlib
import base64
import requests
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

# Load API keys from environment
OKX_API_KEY = os.environ.get("OKX_API_KEY")
OKX_SECRET_KEY = os.environ.get("OKX_SECRET_KEY")
OKX_PASSPHRASE = os.environ.get("OKX_PASSPHRASE")

BASE_URL = "https://www.okx.com"

HEADERS = {
    "Content-Type": "application/json",
    "OK-ACCESS-KEY": OKX_API_KEY,
    "OK-ACCESS-PASSPHRASE": OKX_PASSPHRASE,
}

# Generate signature
def generate_signature(timestamp, method, request_path, body=""):
    message = f"{timestamp}{method}{request_path}{body}"
    mac = hmac.new(bytes(OKX_SECRET_KEY, encoding="utf8"), msg=message.encode("utf-8"), digestmod=hashlib.sha256)
    return base64.b64encode(mac.digest()).decode("utf-8")

# Place order
def place_order(signal, pair, entry, sl, tp1, tp2, risk):
    timestamp = str(time.time())
    symbol = pair.replace("-", "").upper()
    side = "buy" if signal == "LONG" else "sell"

    # Calculate size based on 376 USDT capital
    notional = 376 * float(risk.strip("%")) / 100
    size = round(notional / entry, 4)

    order = {
        "instId": symbol,
        "tdMode": "cross",
        "side": side,
        "ordType": "market",
        "sz": str(size),
    }

    body = json.dumps(order)
    signature = generate_signature(timestamp, "POST", "/api/v5/trade/order", body)

    HEADERS.update({
        "OK-ACCESS-SIGN": signature,
        "OK-ACCESS-TIMESTAMP": timestamp,
    })

    url = f"{BASE_URL}/api/v5/trade/order"
    res = requests.post(url, headers=HEADERS, data=body)
    return res.json()

# Webhook endpoint
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    try:
        signal = data["signal"]
        pair = data["pair"]
        entry = float(data["entry"])
        sl = float(data["sl"])
        tp1 = float(data["tp1"])
        tp2 = float(data["tp2"])
        risk = data["risk"]

        response = place_order(signal, pair, entry, sl, tp1, tp2, risk)
        return jsonify({"status": "Order sent", "okx_response": response})
    except Exception as e:
        return jsonify({"status": "Error", "message": str(e)})

# Run the Flask app properly on Render
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))


