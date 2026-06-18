# -*- coding: utf-8 -*-

import gspread
from google.oauth2 import service_account
import telebot
import yfinance as yf
from datetime import datetime
import pytz
import os
import json
from flask import Flask, request

# CONFIG

SERVICE_ACCOUNT_JSON = os.environ.get('SERVICE_ACCOUNT_JSON')
SPREADSHEET_ID = '1Fq8dKl_72XqdrAcA6atIl5kD23lnkYKSzH4wVNCyQUs'
BOT_TOKEN = 'YOUR_NEW_TOKEN'
BOT_CHAT_ID = '615256683'

IST = pytz.timezone('Asia/Kolkata')

# GOOGLE SHEETS

def connect_to_sheets():
credentials_dict = json.loads(SERVICE_ACCOUNT_JSON)
credentials = service_account.Credentials.from_service_account_info(
credentials_dict,
scopes=[
'https://www.googleapis.com/auth/spreadsheets',
'https://www.googleapis.com/auth/drive'
]
)
gc = gspread.Client(auth=credentials)
return gc.open_by_key(SPREADSHEET_ID).sheet1

def read_sheet_data():
sheet = connect_to_sheets()
data = sheet.get_all_values()

```
if len(data) < 2:
    return []

stocks = []
for row in data[1:]:
    if len(row) < 13 or row[8] == '':
        continue

    try:
        stocks.append({
            'name': row[1],
            'ID': row[3],
            'trigger': float(row[8]),
            'remarks': row[12]
        })
    except:
        continue

return stocks
```

# STOCK DATA

def get_live_price(symbol):
try:
data = yf.Ticker(symbol).history(period='1d')
return data['Close'].iloc[-1] if len(data) > 0 else None
except:
return None

def send_telegram_alert(stock, price):
message = f"""🚨 ALERT! 🚨

Stock: {stock['name']} ({stock['ID']})
Trigger: ₹{stock['trigger']}
Current: ₹{price:.2f}
Remarks: {stock['remarks']}"""

```
bot = telebot.TeleBot(BOT_TOKEN)
bot.send_message(BOT_CHAT_ID, message)
```

# MAIN LOGIC

def monitor_stocks():
now = datetime.now(IST)
print(f"⏰ IST Time: {now}")

```
# Weekdays only
if now.weekday() >= 5:
    print("Weekend - Skip")
    return

# Market hours
start = now.replace(hour=9, minute=15, second=0, microsecond=0)
end = now.replace(hour=15, minute=30, second=0, microsecond=0)

if not (start <= now <= end):
    print("Outside market hours")
    return

stocks = read_sheet_data()

for stock in stocks:
    price = get_live_price(stock['ID'])
    if price and price >= stock['trigger']:
        send_telegram_alert(stock, price)
        print(f"Alert sent: {stock['name']}")
    elif price:
        print(f"{stock['name']}: ₹{price:.2f}")
```

# FLASK

app = Flask(**name**)

@app.route("/")
def home():
return "Server is running"

@app.route("/run")
def run():
key = request.args.get("key")

```
if key != "secret123":
    return "Unauthorized", 403

monitor_stocks()
return "Executed"
```

# START

if **name** == "**main**":
port = int(os.environ.get("PORT", 10000))
app.run(host="0.0.0.0", port=port)
