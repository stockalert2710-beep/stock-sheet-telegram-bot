# -*- coding: utf-8 -*-
import gspread
from google.oauth2 import service_account
import telebot
import yfinance as yf
import datetime
import time
import os
import json
import schedule
from flask import Flask, request

SERVICE_ACCOUNT_JSON = os.environ.get('SERVICE_ACCOUNT_JSON')
SPREADSHEET_ID = '1Fq8dKl_72XqdrAcA6atIl5kD23lnkYKSzH4wVNCyQUs'
BOT_TOKEN = '8988067878:AAHk4G1XsUicBOtfoG_yfLugt9uhtuYus9k'
BOT_CHAT_ID = '615256683'

# Exchange suffix mapping for yfinance
EXCHANGE_SUFFIX = {
    'NSE': '.NS',
    'BSE': '.BO'
}

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
    sh = gc.open_by_key(SPREADSHEET_ID)
    sheet = sh.sheet1
    return sheet

def read_sheet_data():
    sheet = connect_to_sheets()
    data = sheet.get_all_values()
    
    print(f"\n📄 Total rows: {len(data)}")
    
    if len(data) < 2:
        return []
    
    stocks = []
    for i, row in enumerate(data[1:], 1):
        print(f"\n🔍 Row {i}: len={len(row)}")
        
        if len(row) < 13:
            print(f"  Skip: less than 13 cols")
            continue
        
        if row[8] == '':
            print(f"  Skip: empty Trigger")
            continue
        
        try:
            # Get exchange from column C (index 2)
            exchange = row[2]
            ID = row[3]
            
            # Format symbol with exchange suffix
            formatted_symbol = get_formatted_symbol(ID, exchange)
            print(f"  📝 Exchange: {exchange}, ID: {ID} -> Formatted: {formatted_symbol}")
            
            # Get condition from column J (index 9) - "more than" or "less than"
            condition = row[9].lower().strip() if row[9] else ''
            
            if condition not in ['more than', 'less than']:
                print(f"  Skip: invalid condition '{row[9]}' (must be 'more than' or 'less than')")
                continue
            
            stocks.append({
                'name': row[1],
                'exchange': exchange,
                'ID': ID,
                'symbol': formatted_symbol,  # New field with formatted symbol
                'elliot_position': row[5],
                'price_bo': row[6],
                'rsi_bo': row[7],
                'trigger': float(row[8]),
                'condition': condition,  # New field for condition
                'SL': row[10],
                'T&T': row[11],
                'remarks': row[12]
            })
            print(f"  ✅ Added: {row[1]} (Condition: {condition}, Trigger: {row[8]})")
        except ValueError as e:
            print(f"  ❌ Skip: {e}")
    
    print(f"\n📊 Total: {len(stocks)} stocks")
    return stocks

def get_formatted_symbol(ID, exchange):
    """
    Add exchange suffix to ID based on exchange type
    NSE -> .NS, BSE -> .BO
    """
    if exchange in EXCHANGE_SUFFIX:
        return ID + EXCHANGE_SUFFIX[exchange]
    return ID  # Return as-is if exchange not recognized

def get_live_price(symbol):
    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period='1d')
        return data['Close'].iloc[-1] if len(data) > 0 else None
    except:
        return None

def check_alert_triggered(cmp, trigger, condition):
    """
    Check if alert should be triggered based on condition
    condition = 'more than' -> cmp >= trigger
    condition = 'less than' -> cmp <= trigger
    """
    if condition == 'more than':
        return cmp >= trigger
    elif condition == 'less than':
        return cmp <= trigger
    return False

def send_telegram_alert(stock):
    current_price = get_live_price(stock['symbol'])
    message = f"""🚨 ALERT! 🚨

Stock: {stock['name']} ({stock['ID']})
Exchange: {stock['exchange']}
Condition: {stock['condition'].upper()}
Trigger: ₹{stock['trigger']}
Current: ₹{current_price}
Remarks: {stock['remarks']}"""
    
    bot = telebot.TeleBot(BOT_TOKEN)
    bot.send_message(BOT_CHAT_ID, message)

def monitor_stocks():
    print(f"\n⏰ Running stock check at {datetime.datetime.now()}")
    
    print("✅ Proceeding with stock monitoring...")
    stocks = read_sheet_data()
    print(f"\n📦 Stocks: {stocks}")
    
    if len(stocks) == 0:
        print("No stocks")
        return
    
    for stock in stocks:
        # Use formatted symbol with exchange suffix
        price = get_live_price(stock['symbol'])
        if price:
            # Check if alert should be triggered based on condition
            if check_alert_triggered(price, stock['trigger'], stock['condition']):
                send_telegram_alert(stock)
                print(f"✓ Alert: {stock['name']} ({stock['condition']})")
            else:
                condition_symbol = '>' if stock['condition'] == 'more than' else '<'
                print(f"✓ {stock['name']} ({stock['exchange']}): ₹{price:.2f} {condition_symbol} ₹{stock['trigger']}")
        else:
            print(f"⚠️ No price data for {stock['name']}")

def run_periodically():
    """Run monitor_stocks every 15 minutes"""
    print("🔄 Starting periodic stock monitor (15 min intervals)")
    
    # Run immediately
    monitor_stocks()
    
    # Schedule every 15 minutes
    schedule.every(15).minutes.do(monitor_stocks)
    
    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    # Check if running as cron job or periodically
    if os.environ.get('RUN_PERIODICALLY') == 'true':
        run_periodically()
    else:
        monitor_stocks()

app = Flask(__name__)

@app.route("/")
def home():
    return "Server is running"

@app.route("/run")
def run():
    key = request.args.get("key")
    
    if key != "secret123":
        return "Unauthorized", 403

    monitor_stocks()
    return "Script executed"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
