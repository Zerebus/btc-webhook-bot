
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
        server_ts = int(res.json()["data"][0]["ts"])
        local_ts = int(time.time() * 1000)
        diff = local_ts - server_ts
        iso_timestamp = datetime.utcfromtimestamp(server_ts / 1000).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        print(f"[DEBUG] OKX Server Timestamp: {server_ts} ({iso_timestamp})")
        print(f"[DEBUG] Local Timestamp: {local_ts} — Difference: {diff} ms")
        return iso_timestamp
    except Exception as e:
        print("[ERROR] Failed to fetch OKX server time:", e)
        fallback = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        print("[DEBUG] Using fallback ISO timestamp:", fallback)
        return fallback

def generate_signature(timestamp, method, request_path, body=""):
    message = f"{timestamp}{method}{request_path}{body}"
    mac = hmac.new(bytes(OKX_SECRET_KEY, encoding='utf-8'),
                   bytes(message, encoding='utf-8'), hashlib.sha256)
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
        print("[ERROR] Failed to fetch balance:", e)
    return 1000.0  # fallback default balance

def place_order(signal, pair, entry, sl, tp1, tp2, risk):
    timestamp = fetch_okx_server_timestamp()
    symbol = pair.replace("-", "/").upper()
    side = "buy" if signal == "LONG" else "sell"

    risk_percent = max(float(risk.strip('%')), 3.5)
    usdt_balance = get_usdt_balance()
    notional = usdt_balance * risk_percent / 100
    size = round(notional / entry, 4)

    if notional < 10:
        print(f"[WARNING] Notional too low (${notional:.2f}). Skipping order.")
        return {"reason": "Notional too low", "notional": notional, "status": "Rejected"}

    order = {
        "instId": pair,
        "tdMode": "cross",
        "side": side,
        "ordType": "market",
        "sz": str(size)
    }

    body = json.dumps(order)
    signature = generate_signature(timestamp, "POST", "/api/v5/trade/order", body)

    headers = HEADERS.copy()
    headers.update({
        "OK-ACCESS-SIGN": signature,
        "OK-ACCESS-TIMESTAMP": timestamp
    })

    url = f"{BASE_URL}/api/v5/trade/order"
    print("[DEBUG] Sending order to OKX:", json.dumps(order, indent=2))
    print("[DEBUG] Timestamp used:", timestamp)
    print("[DEBUG] Headers:", headers)

    res = requests.post(url, headers=headers, data=body)
    print("[DEBUG] OKX Raw Response:", res.status_code, res.text)
    return res.json()

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    try:
        print("[DEBUG] Incoming Webhook Data:", data)
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
        print("[ERROR] Webhook Exception:", str(e))
        return jsonify({"status": "Error", "message": str(e)})

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=10000)
