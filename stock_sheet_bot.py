# -*- coding: utf-8 -*-
import gspread
from google.oauth2 import service_account
import telebot
import yfinance as yf
import datetime
import time

# ===== CONFIGURATION =====
SERVICE_ACCOUNT_FILE = 'service_account.json'
SPREADSHEET_NAME = 'Stock Alerts'
BOT_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN_HERE'
BOT_CHAT_ID = 'YOUR_TELEGRAM_CHAT_ID_HERE'

def connect_to_sheets():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    gc = gspread.Client(auth=credentials)
    sh = gc.open(SPREADSHEET_NAME)
    sheet = sh.sheet1
    return sheet

def read_sheet_data():
    sheet = connect_to_sheets()
    data = sheet.get_all_values()
    if len(data) < 2:
        return []
    
    stocks = []
    for row in data[1:]:
        if len(row) >= 9:
            stocks.append({
                'name': row[0],
                'symbol': row[1],
                'sector': row[2],
                'industry': row[3],
                'cmp': float(row[6]),
                'trigger': float(row[7]),
                'condition': row[8]
            })
    return stocks

def get_live_price(symbol):
    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period='1d')
        if len(data) > 0:
            return data['Close'].iloc[-1]
        return None
    except:
        return None

def check_alert_triggered(cmp, trigger, condition):
    if condition == 'more than':
        return cmp >= trigger
    elif condition == 'less than':
        return cmp <= trigger
    return False

def send_telegram_alert(stock):
    message = f"""🚨 **ALERT TRIGGERED!** 🚨

📊 Stock: {stock['name']} ({stock['symbol']})
Sector: {stock['sector']}
Industry: {stock['industry']}

💰 Price Alert:
• CMP: ₹{stock['cmp']:.2f}
• Trigger: ₹{stock['trigger']}
• Condition: {stock['condition']}

⏰ {datetime.now().strftime('%d %b %Y, %H:%M:%S')}"""
    
    bot = telebot.Bot(BOT_TOKEN)
    bot.send_message(BOT_CHAT_ID, message, parse_mode='Markdown')

def monitor_stocks():
    print(f"\n🔍 Checking stocks at {datetime.now()}...")
    stocks = read_sheet_data()
    
    if len(stocks) == 0:
        print("No stocks found")
        return
    
    print(f"Monitoring {len(stocks)} stocks...")
    
    for stock in stocks:
        live_price = get_live_price(stock['symbol'])
        if live_price:
            if check_alert_triggered(live_price, stock['trigger'], stock['condition']):
                send_telegram_alert(stock)
                print(f"✓ Alert sent for {stock['name']}")
            else:
                print(f"✓ {stock['name']}: ₹{live_price:.2f}")

if __name__ == "__main__":
    monitor_stocks()
