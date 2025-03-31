import time
import hmac
import hashlib
import base64
import requests
import json
from flask import Flask, request

app = Flask(__name__)

# === OKX API Credentials ===
API_KEY = "your_api_key"
API_SECRET = "your_api_secret"
PASSPHRASE = "your_passphrase"
BASE_URL = "https://www.okx.com"

# === Utility: Timestamp ===
def get_timestamp():
    return str(int(time.time() * 1000))

# === Utility: OKX Signature ===
def generate_signature(timestamp, method, request_path, body):
    if not body:
        body = ""
    message = f"{timestamp}{method.upper()}{request_path}{body}"
    mac = hmac.new(API_SECRET.encode(), message.encode(), hashlib.sha256)
    d = mac.digest()
    return base64.b64encode(d).decode()

# === Core: Order Execution ===
def place_order(signal, pair, entry, sl, tp1, tp2, risk, test=False):
    timestamp = get_timestamp()
    path = "/api/v5/trade/order"
    method = "POST"

    size = 1  # Simplified; replace with position sizing logic
    side = "buy" if signal == "LONG" else "sell"
    posSide = "long" if signal == "LONG" else "short"

    body_data = {
        "instId": pair,
        "tdMode": "cross",
        "side": side,
        "ordType": "market",
        "posSide": posSide,
        "sz": str(size)
    }

    body = json.dumps(body_data)
    signature = generate_signature(timestamp, method, path, body)

    headers = {
        "OK-ACCESS-KEY": API_KEY,
        "OK-ACCESS-SIGN": signature,
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": PASSPHRASE,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(f"{BASE_URL}{path}", headers=headers, data=body)
        print("🌐 OKX Response:", response.text)
        return response.text
    except Exception as e:
        print("❌ Error placing order:", str(e))
        return str(e)

# === Webhook Route ===
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        print("✅ Webhook received:", data)

        signal = data.get("signal")
        pair = data.get("pair")
        sl_pct = data.get("sl_pct")
        tp1_pct = data.get("tp1_pct")
        tp2_pct = data.get("tp2_pct")
        risk = data.get("risk")
        test = data.get("test", False)

        # Validate required fields
        if not all([signal, pair, sl_pct, tp1_pct, tp2_pct, risk]):
            print("❌ Missing one or more required fields in webhook payload.")
            return {"status": "missing fields", "message": data}, 400

        print("📊 Payload parsed. Placing order...")
        result = place_order(signal, pair, None, None, None, None, risk, test=test)

        return {"status": "Order sent", "okx_response": result}, 200

    except Exception as e:
        print("🔥 Error in webhook:", e)
        return {"status": "error", "message": str(e)}, 500

# === Health Check Route ===
@app.route("/healthz")
def health():
    return "ok", 200

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=10000)

