
from flask import Flask, request
import os
import requests
import time
import hmac
import hashlib
import json

app = Flask(__name__)

API_KEY = os.getenv('BITGET_API_KEY')
API_SECRET = os.getenv('BITGET_API_SECRET')
API_PASSPHRASE = os.getenv('BITGET_API_PASSPHRASE')

BASE_URL = "https://api.bitget.com"

def generate_signature(timestamp, method, request_path, body):
    prehash = str(timestamp) + method + request_path + body
    signature = hmac.new(API_SECRET.encode('utf-8'), prehash.encode('utf-8'), hashlib.sha256).hexdigest()
    return signature

def get_headers(timestamp, method, request_path, body):
    signature = generate_signature(timestamp, method, request_path, body)
    headers = {
        'Content-Type': 'application/json',
        'ACCESS-KEY': API_KEY,
        'ACCESS-SIGN': signature,
        'ACCESS-TIMESTAMP': str(timestamp),
        'ACCESS-PASSPHRASE': API_PASSPHRASE,
        'locale': 'en-US'
    }
    return headers

def get_kaspa_balance():
    timestamp = int(time.time() * 1000)
    request_path = "/api/spot/v1/account/assets"
    url = BASE_URL + request_path
    headers = get_headers(timestamp, "GET", request_path, "")
    response = requests.get(url, headers=headers)
    print("📦 Svar från Bitget (saldo):", response.json())
    assets = response.json()

    if assets['code'] == "00000":
        for asset in assets['data']:
            if asset['coinName'] == "KASPA":
                return float(asset['available'])
    return 0.0

def place_order(symbol, side, quantity_type, quantity_value):
    timestamp = int(time.time() * 1000)
    request_path = "/api/spot/v1/trade/order"
    url = BASE_URL + request_path

    order = {
        "symbol": symbol,
        "side": side,
        "orderType": "market",
        "force": "gtc"
    }

    if quantity_type == "quote":
        order["quoteOrderQty"] = str(quantity_value)
    elif quantity_type == "base":
        order["baseQuantity"] = str(quantity_value)

    body = json.dumps(order)
    headers = get_headers(timestamp, "POST", request_path, body)
    print("⚙️ Orderdata:", order)
    response = requests.post(url, headers=headers, data=body)
    print("📨 Svar från Bitget:", response.json())
    return response.json()

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        try:
            data = request.get_json(force=True)
            print("✅ Mottagen JSON:", data)
        except Exception as e:
            print("❌ Kunde inte läsa JSON:", str(e))
            return {"error": "Invalid JSON"}, 400

        side = data.get("side")

        if side == "buy_request":
            print("👉 Initierar köp...")
            return place_order("KASPAUSDT", "buy", "quote", 10)
        elif side == "sell_request":
            print("👉 Initierar sälj...")
            balance = get_kaspa_balance()
            return place_order("KASPAUSDT", "sell", "base", balance)
        else:
            print("❌ Ogiltig side:", side)
            return {"error": "Invalid side"}, 400

    except Exception as e:
        print("🚨 Fel i webhook:", str(e))
        return {"error": "Server error"}, 500

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    app.run(host="0.0.0.0", port=port)
