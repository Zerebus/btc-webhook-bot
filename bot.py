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

open_trades = {}

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

def is_market_volatile_enough(pair, threshold=0.75, lookback=10):
    try:
        url = f"{BASE_URL}/api/v5/market/candles?instId={pair}&bar=15m&limit={lookback}"
        res = requests.get(url)
        candles = res.json()["data"]

        high_prices = [float(c[2]) for c in candles]
        low_prices = [float(c[3]) for c in candles]
        max_high = max(high_prices)
        min_low = min(low_prices)

        range_percent = ((max_high - min_low) / min_low) * 100
        print(f"[VOLATILITY] {pair} range over last {lookback} candles: {range_percent:.2f}%")

        return range_percent >= threshold
    except Exception as e:
        print("[ERROR] Volatility check failed:", e)
        return True  # Fallback to allow trade


def set_leverage(pair, leverage, mode="cross"):
    timestamp = fetch_okx_server_timestamp()
    method = "POST"
    request_path = "/api/v5/account/set-leverage"

    leverage = min(int(leverage), 5)  # Cap leverage at 5x
    payload = {
        "instId": pair,
        "lever": str(leverage),
        "mgnMode": mode
    }
    body = json.dumps(payload)
    signature = generate_signature(timestamp, method, request_path, body)

    headers = HEADERS.copy()
    headers.update({
        "OK-ACCESS-SIGN": signature,
        "OK-ACCESS-TIMESTAMP": timestamp
    })

    try:
        print(f"[LEVERAGE] Setting leverage to {leverage}x for {pair}")
        res = requests.post(f"{BASE_URL}{request_path}", headers=headers, data=body)
        print("[LEVERAGE] Response:", res.status_code, res.text)
    except Exception as e:
        print("[ERROR] Leverage setup failed:", e)


def fetch_okx_server_timestamp():
    try:
        res = requests.get(f"{BASE_URL}/api/v5/public/time")
        return str(float(res.json()["data"][0]["ts"]) / 1000)  # convert ms to sec
    except Exception as e:
        print("[ERROR] Fetching server timestamp:", e)
        return str(time.time())  # fallback to system time in sec

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

    # Estimate dynamic leverage from stop size and risk
    stop_pct = abs(entry - sl) / entry
    leverage = max(1, min(int((risk_percent / stop_pct)), 5))
    set_leverage(pair, leverage)

# Volatility filter
    if not is_market_volatile_enough(pair):
        print(f"[INFO] Market volatility too low for {pair}. Trade blocked.")
        return {"status": "blocked", "reason": "low volatility"}
    # Daily loss limit check
    today = datetime.utcnow().date()
    if daily_loss > DAILY_LOSS_LIMIT:
        print(f"[WARNING] Daily loss limit hit: {daily_loss}%")
        return {"status": "blocked", "reason": "daily loss limit"}

    # Cooldown check
    if pair in cooldown_until and datetime.utcnow() < cooldown_until[pair]:
        print(f"[INFO] Cooldown active for {pair} until {cooldown_until[pair]}")
        return {"status": "blocked", "reason": "cooldown active"}

    # Check if a trade is already open for this pair
    if open_trades.get(pair, False):
        print(f"[INFO] Skipping trade: already open for {pair}")
        return {"status": "skipped", "reason": "duplicate trade"}

    open_trades[pair] = True  # Lock the trade

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

    try:
        order_id = response.json()["data"][0]["ordId"]
        print("[DEBUG] Primary order ID:", order_id)

        # Split position size: 50% for TP1, 50% for TP2
        tp1_size = round(size * 0.5, 6)
        tp2_size = round(size * 0.5, 6)

        common_tp_sl = {
            "instId": pair,
            "tdMode": "cross",
            "side": "sell" if side == "buy" else "buy",
            "ordType": "trigger",
            "reduceOnly": True
        }

        # TP1 Order
        tp1_order = common_tp_sl.copy()
        tp1_order.update({
            "triggerPx": str(tp1),
            "px": str(tp1),
            "sz": str(tp1_size)
        })
        tp1_body = json.dumps(tp1_order)
        tp1_signature = generate_signature(timestamp, method, request_path, tp1_body)
        tp1_headers = HEADERS.copy()
        tp1_headers.update({
            "OK-ACCESS-SIGN": tp1_signature,
            "OK-ACCESS-TIMESTAMP": timestamp
        })
        tp1_res = requests.post(f"{BASE_URL}{request_path}", headers=tp1_headers, data=tp1_body)

        # Launch trailing stop thread after TP1
        threading.Thread(
            target=monitor_trailing_stop,
            args=(pair, entry, tp2_size, side),
            daemon=True
        ).start()

        print("[DEBUG] TP1 Order Response:", tp1_res.status_code, tp1_res.text)

        # TP2 Order
        tp2_order = common_tp_sl.copy()
        tp2_order.update({
            "triggerPx": str(tp2),
            "px": str(tp2),
            "sz": str(tp2_size)
        })
        tp2_body = json.dumps(tp2_order)
        tp2_signature = generate_signature(timestamp, method, request_path, tp2_body)
        tp2_headers = HEADERS.copy()
        tp2_headers.update({
            "OK-ACCESS-SIGN": tp2_signature,
            "OK-ACCESS-TIMESTAMP": timestamp
        })
        tp2_res = requests.post(f"{BASE_URL}{request_path}", headers=tp2_headers, data=tp2_body)
        print("[DEBUG] TP2 Order Response:", tp2_res.status_code, tp2_res.text)

        # SL for full size
        sl_order = common_tp_sl.copy()
        sl_order.update({
            "triggerPx": str(sl),
            "px": str(sl),
            "sz": str(size)
        })
        sl_body = json.dumps(sl_order)
        sl_signature = generate_signature(timestamp, method, request_path, sl_body)
        sl_headers = HEADERS.copy()
        sl_headers.update({
            "OK-ACCESS-SIGN": sl_signature,
            "OK-ACCESS-TIMESTAMP": timestamp
        })
        sl_res = requests.post(f"{BASE_URL}{request_path}", headers=sl_headers, data=sl_body)
        print("[DEBUG] SL Order Response:", sl_res.status_code, sl_res.text)

    except Exception as e:
        print("[ERROR] Multi-TP/SL Order Failed:", e)


    # After placing the market order, set TP and SL orders using trigger orders
    try:
        order_id = response.json()["data"][0]["ordId"]
        print("[DEBUG] Primary order ID:", order_id)

        # Take Profit Order
        tp_order = {
            "instId": pair,
            "tdMode": "cross",
            "side": "sell" if side == "buy" else "buy",
            "ordType": "trigger",
            "triggerPx": str(tp1),
            "sz": str(size),
            "px": str(tp1),
            "reduceOnly": True
        }
        tp_body = json.dumps(tp_order)
        tp_signature = generate_signature(timestamp, method, request_path, tp_body)
        tp_headers = HEADERS.copy()
        tp_headers.update({
            "OK-ACCESS-SIGN": tp_signature,
            "OK-ACCESS-TIMESTAMP": timestamp
        })
        tp_res = requests.post(f"{BASE_URL}{request_path}", headers=tp_headers, data=tp_body)
        print("[DEBUG] TP Order Response:", tp_res.status_code, tp_res.text)

        # Stop Loss Order
        sl_order = {
            "instId": pair,
            "tdMode": "cross",
            "side": "sell" if side == "buy" else "buy",
            "ordType": "trigger",
            "triggerPx": str(sl),
            "sz": str(size),
            "px": str(sl),
            "reduceOnly": True
        }
        sl_body = json.dumps(sl_order)
        sl_signature = generate_signature(timestamp, method, request_path, sl_body)
        sl_headers = HEADERS.copy()
        sl_headers.update({
            "OK-ACCESS-SIGN": sl_signature,
            "OK-ACCESS-TIMESTAMP": timestamp
        })
        sl_res = requests.post(f"{BASE_URL}{request_path}", headers=sl_headers, data=sl_body)
        print("[DEBUG] SL Order Response:", sl_res.status_code, sl_res.text)

    except Exception as e:
        print("[ERROR] TP/SL Order Failed:", e)


    
    open_trades[pair] = False  # Unlock after sending TP/SL

    # Simulated outcome for PnL tracking
    mock_exit_price = latest_price * 0.98 if side == "buy" else latest_price * 1.02
    pnl = (mock_exit_price - entry) if side == "buy" else (entry - mock_exit_price)
    pnl_percent = (pnl / entry) * 100
    print(f"[DEBUG] Simulated PnL %: {pnl_percent:.2f}")

    if pnl_percent < 0:
        daily_loss += abs(pnl_percent)
        cooldown_until[pair] = datetime.utcnow() + timedelta(minutes=COOLDOWN_MINUTES)
        print(f"[INFO] Cooldown triggered for {pair} until {cooldown_until[pair]}")


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

