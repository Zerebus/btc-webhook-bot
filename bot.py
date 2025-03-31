import os
import hmac
import json
import time
import base64
import hashlib
import requests
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# ENV variables
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
        return res.json()["data"][0]["ts"]
    except Exception as e:
        print("[ERROR] Fetching server timestamp:", e)
        return str(int(time.time() * 1000))

def generate_signature(timestamp, method, request_path, body=""):
    message = f"{timestamp}{method}{request_path}{body}"
    mac = hmac.new(bytes(OKX_SECRET_KEY, encoding='utf-8'),
                   bytes(message, encoding='utf-8'),
                   digestmod=hashlib.sha256)
    return base64.b64encode(mac.digest()).decode()

def get_usdt_balance():
    timestamp = fetch_okx_server_timestamp()
    signature = generate_signature(timestamp, "GET", "/api/v5/account/balance")

    headers = HEADERS.copy()
    headers.update({
        "OK-ACCESS-SIGN": signature,
        "OK-ACCESS-TIMESTAMP": timestamp
    })

    try:
        res = requests.get(f"{BASE_URL}/api/v5/account/balance", headers=headers)
        balances = res.json()["data"][0]["details"]
        for asset in balances:
            if asset["ccy"] == "USDT":
                usdt_balance = float(asset["cashBal"])
                print("[DEBUG] USDT Balance:", usdt_balance)
                return usdt_balance
    except Exception as e:
        print("[ERROR] Balance fetch failed:", e)
    return 100.0  # Fallback value

def get_latest_price(instId="BTC-USDT"):
    try:
        res = requests.get(f"{BASE_URL}/api/v5/market/ticker?instId={instId}")
        return float(res.json()["data"][0]["last"])
    except Exception as e:
        print("[ERROR] Price fetch failed:", e)
        return 83000  # Fallback price

def place_order(signal, pair, entry, sl, tp1, tp2, risk):
    timestamp = fetch_okx_server_timestamp()
    method = "POST"
    request_path = "/api/v5/trade/order"

    latest_price = get_latest_price(pair)
    side = "buy" if signal.upper() == "LONG" else "sell"

    usdt_balance = get_usdt_balance()
    risk_percent = float(str(risk).strip('%')) if '%' in str(risk) else float(risk)
    notional = usdt_balance * (risk_percent / 100)

    # Safety cap and floor
    if notional < 5:
        notional = 5
    elif notional > usdt_balance:
        notional = usdt_balance

    size = round(notional / latest_price, 6)

    order = {
        "instId": pair,
        "tdMode": "cross",
        "side": side,
        "ordType": "market",
        "sz": str(size)
    }

    body = json.dumps(order)
    signature = generate_signature(timestamp, method, request_path, body)

    headers = HEADERS.copy()
    headers.update({
        "OK-ACCESS-SIGN": signature,
        "OK-ACCESS-TIMESTAMP": timestamp
    })

    print("[DEBUG] Submitting order:", order)
    print("[DEBUG] Entry Price (live):", latest_price)
    print("[DEBUG] Risk %:", risk_percent, "| USDT:", usdt_balance, "| Size:", size)

    response = requests.post(f"{BASE_URL}{request_path}", headers=headers, data=body)
    print("[DEBUG] Response:", response.status_code, response.text)

    return response.json()

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print("[DEBUG] Webhook received:", data)

    try:
        response = place_order(
            data['signal'],
            data['pair'],
            float(data['entry']),
            float(data['sl']),
            float(data['tp1']),
            float(data['tp2']),
            data['risk']
        )
        return jsonify({"status": "Order sent", "okx_response": response})
    except Exception as e:
        print("[ERROR] Webhook processing failed:", str(e))
        return jsonify({"status": "Error", "message": str(e)})

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=10000)

