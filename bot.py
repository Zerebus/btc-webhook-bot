import os
import time
import hmac
import hashlib
import base64
import requests
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

# Load API keys securely from environment
OKX_API_KEY = os.environ.get("OKX_API_KEY")
OKX_SECRET_KEY = os.environ.get("OKX_SECRET_KEY")
OKX_PASSPHRASE = os.environ.get("OKX_PASSPHRASE")

BASE_URL = "https://www.okx.com"

# Generate OKX signature
def generate_signature(timestamp, method, request_path, body=""):
    message = f"{timestamp}{method}{request_path}{body}"
    mac = hmac.new(bytes(OKX_SECRET_KEY, encoding='utf-8'), msg=message.encode('utf-8'), digestmod=hashlib.sha256)
    return base64.b64encode(mac.digest()).decode()

# Build and send order to OKX
def place_order(signal, pair, entry, sl, tp1, tp2, risk):
    timestamp = str(int(time.time() * 1000))  # Millisecond timestamp
    symbol = pair.replace("-", "/").upper()
    side = "buy" if signal == "LONG" else "sell"

    # Calculate order size
    notional = 376 * float(risk.strip('%')) / 100
    size = round(notional / entry, 4)

    order = {
        "instId": pair,
        "tdMode": "cross",
        "side": side,
        "ordType": "market",
        "sz": str(size)
    }

    body = json.dumps(order)
    request_path = "/api/v5/trade/order"
    signature = generate_signature(timestamp, "POST", request_path, body)

    headers = {
        "Content-Type": "application/json",
        "OK-ACCESS-KEY": OKX_API_KEY,
        "OK-ACCESS-SIGN": signature,
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": OKX_PASSPHRASE
    }

    url = f"{BASE_URL}{request_path}"
    res = requests.post(url, headers=headers, data=body)
    return res.json()

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    required_keys = ["signal", "pair", "entry", "sl", "tp1", "tp2", "risk"]
    if not all(k in data for k in required_keys):
        return jsonify({"status": "Error", "message": "Missing required fields"}), 400

    try:
        entry = float(data['entry'])
        sl = float(data['sl'])
        tp1 = float(data['tp1'])
        tp2 = float(data['tp2'])
    except ValueError:
        return jsonify({"status": "Error", "message": "Invalid numeric values"}), 400

    okx_response = place_order(
        signal=data['signal'],
        pair=data['pair'],
        entry=entry,
        sl=sl,
        tp1=tp1,
        tp2=tp2,
        risk=data['risk']
    )

    return jsonify({"status": "Order sent", "okx_response": okx_response})

if __name__ == "__main__":
    app.run(debug=True, port=5000)


