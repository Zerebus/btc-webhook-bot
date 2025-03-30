import os
import time
import hmac
import hashlib
import base64
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Load API keys from environment variables
OKX_API_KEY = os.environ.get("OKX_API_KEY")
OKX_SECRET_KEY = os.environ.get("OKX_SECRET_KEY")
OKX_PASSPHRASE = os.environ.get("OKX_PASSPHRASE")

BASE_URL = "https://www.okx.com"

# Generate OKX signature
def generate_signature(timestamp, method, request_path, body=""):
    message = f"{timestamp}{method}{request_path}{body}"
    mac = hmac.new(
        bytes(OKX_SECRET_KEY, encoding="utf-8"),
        bytes(message, encoding="utf-8"),
        digestmod=hashlib.sha256
    )
    d = mac.digest()
    return base64.b64encode(d).decode("utf-8")

# Place order
def place_order(signal, pair, entry, sl, tp1, tp2, risk):
    timestamp = str(int(time.time() * 1000))  # milliseconds
    symbol = pair.replace("-", "").upper()
    side = "buy" if signal == "LONG" else "sell"
    notional = 376 * float(risk.strip('%')) / 100
    size = round(notional / entry, 4)

    order = {
        "instId": symbol,
        "tdMode": "cross",
        "side": side,
        "ordType": "market",
        "sz": str(size)
    }

    body = json.dumps(order)
    signature = generate_signature(timestamp, "POST", "/api/v5/trade/order", body)

    headers = {
        "Content-Type": "application/json",
        "OK-ACCESS-KEY": OKX_API_KEY,
        "OK-ACCESS-SIGN": signature,
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": OKX_PASSPHRASE
    }

    url = f"{BASE_URL}/api/v5/trade/order"
    res = requests.post(url, headers=headers, data=body)
    return res.json()

# Webhook endpoint
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    try:
        signal = data["signal"]
        pair = data["pair"]
        entry = float(data["entry"])
        sl = float(data["sl"])
        tp1 = float(data["tp1"])
        tp2 = float(data["tp2"])
        risk = data["risk"]

        res = place_order(signal, pair, entry, sl, tp1, tp2, risk)
        return jsonify({"status": "Order sent", "okx_response": res})

    except Exception as e:
        return jsonify({"status": "Error", "message": str(e)})

# Required for Render deployment
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))


