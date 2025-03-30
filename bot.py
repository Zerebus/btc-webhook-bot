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

HEADERS = {
    "Content-Type": "application/json",
    "OK-ACCESS-KEY": OKX_API_KEY,
    "OK-ACCESS-PASSPHRASE": OKX_PASSPHRASE
}

def generate_signature(timestamp, method, request_path, body=""):
    message = f"{timestamp}{method}{request_path}{body}"
    mac = hmac.new(bytes(OKX_SECRET_KEY, encoding='utf-8'), msg=message.encode('utf-8'), digestmod=hashlib.sha256)
    d = mac.digest()
    return base64.b64encode(d).decode("utf-8")

def place_order(signal, pair, entry, sl, tp1, tp2, risk):
    timestamp = str(int(time.time()))  # UNIX timestamp in seconds as required by OKX
    symbol = pair.replace("-", "").upper()
    side = "buy" if signal == "LONG" else "sell"

    # Calculate order size based on risk and balance
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

    HEADERS.update({
        "OK-ACCESS-SIGN": signature,
        "OK-ACCESS-TIMESTAMP": timestamp
    })

    url = f"{BASE_URL}/api/v5/trade/order"
    res = requests.post(url, headers=HEADERS, data=body)
    return res.json()

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"status": "Error", "message": "Invalid JSON"}), 400

        signal = data.get("signal")
        pair = data.get("pair")
        entry = float(data.get("entry"))
        sl = float(data.get("sl"))
        tp1 = float(data.get("tp1"))
        tp2 = float(data.get("tp2"))
        risk = data.get("risk")

        print("Received order:", data)

        okx_response = place_order(signal, pair, entry, sl, tp1, tp2, risk)
        return jsonify({"okx_response": okx_response, "status": "Order sent"})

    except Exception as e:
        return jsonify({"status": "Error", "message": str(e)})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # For Render compatibility
    app.run(host="0.0.0.0", port=port)


