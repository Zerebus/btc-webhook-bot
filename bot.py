import os
import hmac
import json
import time
import base64
import hashlib
import threading
import requests
from flask import Flask, request, jsonify
from datetime import datetime, timedelta

app = Flask(__name__)

OKX_API_KEY = os.environ.get("OKX_API_KEY")
OKX_SECRET_KEY = os.environ.get("OKX_SECRET_KEY")
OKX_PASSPHRASE = os.environ.get("OKX_PASSPHRASE")
BASE_URL = "https://www.okx.com"

HEADERS = {
    "Content-Type": "application/json",
    "OK-ACCESS-KEY": OKX_API_KEY,
    "OK-ACCESS-PASSPHRASE": OKX_PASSPHRASE
}

open_trades = {}
daily_loss = 0.0
cooldown_until = {}

DAILY_LOSS_LIMIT = 5
COOLDOWN_MINUTES = 10
TRAIL_PERCENT = 1.5

def fetch_okx_server_timestamp():
    try:
        res = requests.get(f"{BASE_URL}/api/v5/public/time")
        return str(float(res.json()["data"][0]["ts"]) / 1000)
    except:
        return str(time.time())

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
                return float(asset["cashBal"])
    except:
        pass
    return 100.0

def get_latest_price(instId="BTC-USDT"):
    try:
        res = requests.get(f"{BASE_URL}/api/v5/market/ticker?instId={instId}")
        return float(res.json()["data"][0]["last"])
    except:
        return 83000

def is_market_volatile_enough(pair, threshold=0.75, lookback=10):
    try:
        url = f"{BASE_URL}/api/v5/market/candles?instId={pair}&bar=15m&limit={lookback}"
        res = requests.get(url)
        candles = res.json()["data"]
        highs = [float(c[2]) for c in candles]
        lows = [float(c[3]) for c in candles]
        range_pct = ((max(highs) - min(lows)) / min(lows)) * 100
        return range_pct >= threshold
    except:
        return True

def set_leverage(pair, leverage, mode="cross"):
    timestamp = fetch_okx_server_timestamp()
    method = "POST"
    path = "/api/v5/account/set-leverage"
    leverage = min(int(leverage), 5)
    payload = {"instId": pair, "lever": str(leverage), "mgnMode": mode}
    body = json.dumps(payload)
    sig = generate_signature(timestamp, method, path, body)
    headers = HEADERS.copy()
    headers.update({
        "OK-ACCESS-SIGN": sig,
        "OK-ACCESS-TIMESTAMP": timestamp
    })
    try:
        requests.post(f"{BASE_URL}{path}", headers=headers, data=body)
    except:
        pass

def monitor_trailing_stop(pair, entry_price, size, side):
    peak = get_latest_price(pair)
    while True:
        time.sleep(10)
        price = get_latest_price(pair)
        if side == "buy":
            if price > peak: peak = price
            if price <= peak * (1 - TRAIL_PERCENT / 100): break
        else:
            if price < peak: peak = price
            if price >= peak * (1 + TRAIL_PERCENT / 100): break
    timestamp = fetch_okx_server_timestamp()
    method = "POST"
    path = "/api/v5/trade/order"
    order = {
        "instId": pair,
        "tdMode": "cross",
        "side": "sell" if side == "buy" else "buy",
        "ordType": "market",
        "sz": str(size)
    }
    body = json.dumps(order)
    sig = generate_signature(timestamp, method, path, body)
    headers = HEADERS.copy()
    headers.update({
        "OK-ACCESS-SIGN": sig,
        "OK-ACCESS-TIMESTAMP": timestamp
    })
    requests.post(f"{BASE_URL}{path}", headers=headers, data=body)

def place_order(signal, pair, entry, sl, tp1, tp2, risk, test=False):
    global daily_loss

    if not test:
        if not is_market_volatile_enough(pair):
            return {"status": "blocked", "reason": "low volatility"}
            return {"status": "blocked", "reason": "low volatility"}
        return {"status": "blocked", "reason": "low volatility"}
    if daily_loss > DAILY_LOSS_LIMIT:
        return {"status": "blocked", "reason": "daily loss limit"}
    if pair in cooldown_until and datetime.utcnow() < cooldown_until[pair]:
        return {"status": "blocked", "reason": "cooldown active"}
    if open_trades.get(pair, False):
        return {"status": "skipped", "reason": "duplicate trade"}
    open_trades[pair] = True

    timestamp = fetch_okx_server_timestamp()
    method = "POST"
    path = "/api/v5/trade/order"
    price = get_latest_price(pair)
    side = "buy" if signal.upper() == "LONG" else "sell"
    balance = get_usdt_balance()
    risk_percent = float(str(risk).strip('%')) if '%' in str(risk) else float(risk)
    notional = max(5, min(balance * risk_percent / 100, balance))
    size = round(notional / price, 6)
    stop_pct = abs(entry - sl) / entry
    leverage = max(1, min(int(risk_percent / stop_pct), 5))
    set_leverage(pair, leverage)

    order = {
        "instId": pair,
        "tdMode": "cross",
        "side": side,
        "ordType": "market",
        "sz": str(size)
    }
    body = json.dumps(order)
    sig = generate_signature(timestamp, method, path, body)
    headers = HEADERS.copy()
    headers.update({
        "OK-ACCESS-SIGN": sig,
        "OK-ACCESS-TIMESTAMP": timestamp
    })
    response = requests.post(f"{BASE_URL}{path}", headers=headers, data=body)

    try:
        tp1_size = round(size * 0.5, 6)
        tp2_size = round(size * 0.5, 6)
        common = {
            "instId": pair,
            "tdMode": "cross",
            "side": "sell" if side == "buy" else "buy",
            "ordType": "trigger",
            "reduceOnly": True
        }
        for target, target_size in [(tp1, tp1_size), (tp2, tp2_size)]:
            tp_order = common.copy()
            tp_order.update({"triggerPx": str(target), "px": str(target), "sz": str(target_size)})
            tp_body = json.dumps(tp_order)
            tp_sig = generate_signature(timestamp, method, path, tp_body)
            tp_headers = headers.copy()
            tp_headers.update({"OK-ACCESS-SIGN": tp_sig})
            requests.post(f"{BASE_URL}{path}", headers=tp_headers, data=tp_body)
        threading.Thread(target=monitor_trailing_stop, args=(pair, entry, tp2_size, side), daemon=True).start()
        sl_order = common.copy()
        sl_order.update({"triggerPx": str(sl), "px": str(sl), "sz": str(size)})
        sl_body = json.dumps(sl_order)
        sl_sig = generate_signature(timestamp, method, path, sl_body)
        sl_headers = headers.copy()
        sl_headers.update({"OK-ACCESS-SIGN": sl_sig})
        requests.post(f"{BASE_URL}{path}", headers=sl_headers, data=sl_body)
    except:
        pass

    mock_exit_price = price * 0.98 if side == "buy" else price * 1.02
    pnl = (mock_exit_price - entry) if side == "buy" else (entry - mock_exit_price)
    pnl_percent = (pnl / entry) * 100
    if pnl_percent < 0:
        daily_loss += abs(pnl_percent)
        cooldown_until[pair] = datetime.utcnow() + timedelta(minutes=COOLDOWN_MINUTES)
    open_trades[pair] = False
    return response.json()

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    try:
        pair = data['pair']
        signal = data['signal']
        risk = data['risk']

        # Support dynamic SL/TP via percentage
        if 'sl_pct' in data and 'tp1_pct' in data and 'tp2_pct' in data:
            entry = get_latest_price(pair)
            sl = entry * (1 - float(data['sl_pct']) / 100) if signal.upper() == 'LONG' else entry * (1 + float(data['sl_pct']) / 100)
            tp1 = entry * (1 + float(data['tp1_pct']) / 100) if signal.upper() == 'LONG' else entry * (1 - float(data['tp1_pct']) / 100)
            tp2 = entry * (1 + float(data['tp2_pct']) / 100) if signal.upper() == 'LONG' else entry * (1 - float(data['tp2_pct']) / 100)
        else:
            entry = float(data['entry'])
            sl = float(data['sl'])
            tp1 = float(data['tp1'])
            tp2 = float(data['tp2'])

        response = place_order(signal, pair, entry, sl, tp1, tp2, risk, test=data.get('test', False))
        return jsonify({"status": "Order sent", "okx_response": response})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=10000)