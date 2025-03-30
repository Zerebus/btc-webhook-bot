import os
import hmac
import json
import time
import base64
import hashlib
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Load secrets from environment
OKX_API_KEY = os.environ.get("OKX_API_KEY")
OKX_SECRET_KEY = os.environ.get("OKX_SECRET_KEY")
OKX_PASSPHRASE = os.environ.get("OKX_PASSPHRASE")
BASE_URL = "https://www.okx.com"

HEADERS = {
    "Content-Type": "application/json",
    "OK-ACCESS-KEY": OKX_API_KEY,
    "OK-ACCESS-PASSPHRASE": OKX_PASSPHRASE
}

def fetch_okx_server_timestamp():
    try:
        res = requests.get(f"{BASE_URL}/api/v5/public/time")
        server_time = res.json()["data"][0]["ts"]
        print("[DEBUG] OKX Server Timestamp:", server_time)
        return server_time
    except Exception as e:
        print("[ERROR] Failed to fetch server timestamp:", e)
        fallback = str(int(time.time() * 1000))
        print("[DEBUG] Fallback timestamp:", fallback)
        return fallback

def generate_signature(timestamp, method, request_path, body=""):
    message = f"{timestamp}{method}{request_path}{body}"
    mac = hmac.new(bytes(OKX_SECRET_KEY, encoding='utf-8'),
                   bytes(message, encoding='utf-8'), hashlib.sha256)
    return base64.b64encode(mac.digest()).decode()

def place_order(signal, pair, entry, sl, tp1, tp2, risk, timestamp):
    symbol = pair.replace("-", "/").upper()
    side = "buy" if signal == "LONG" else "sell"

    risk_percent = max(float(risk.strip('%')), 2.0)
    notional = 376 * risk_percent / 100
    size = round(notional / entry, 4)

    order = {
        "instId": pair,
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
    print("[DEBUG] Sending order to OKX:", json.dumps(order, indent=2))
    print("[DEBUG] Timestamp used:", timestamp)
    print("[DEBUG] Headers:", HEADERS)

    res = requests.post(url, headers=HEADERS, data=body)
    print("[DEBUG] OKX Raw Response:", res.status_code, res.text)

    try:
        return res.json()
    except Exception as e:
        print("[ERROR] Failed to parse OKX response as JSON:", e)
        return res.text

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    try:
        print("[DEBUG] Incoming Webhook Data:", data)
        timestamp = fetch_okx_server_timestamp()
        response = place_order(
            data['signal'],
            data['pair'],
            float(data['entry']),
            float(data['sl']),
            float(data['tp1']),
            float(data['tp2']),
            data['risk'],
            timestamp
        )

        if isinstance(response, dict):
            return jsonify({"status": "Order sent", "okx_response": response})
        else:
            print("[ERROR] Non-JSON response from OKX:", response)
            return jsonify({"status": "Error", "message": "Unexpected response from OKX"})

    except Exception as e:
        print("[ERROR] Webhook Exception:", str(e))
        return jsonify({"status": "Error", "message": str(e)})

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=10000)
