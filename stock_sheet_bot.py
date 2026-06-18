# -*- coding: utf-8 -*-
import gspread
from google.oauth2 import service_account
import telebot
import yfinance as yf
import datetime
import time
import os
import json

# ===== CONFIGURATION =====
SERVICE_ACCOUNT_JSON = os.environ.get('SERVICE_ACCOUNT_JSON')
SPREADSHEET_ID = '1Fq8dKl_72XqdrAcA6atIl5kD23lnkYKSzH4wVNCyQUs'
BOT_TOKEN = os.environ.get('8988067878:AAHk4G1XsUicBOtfoG_yfLugt9uhtuYus9k')
BOT_CHAT_ID = os.environ.get('StockSheetAlertBot')

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
    if len(data) < 2:
        return []
    
    stocks = []
    for row in data[1:]:
        if len(row) >= 9:
            # Skip rows with empty CMP or Trigger
            if row[6] == '' or row[7] == '' or row[8] == '':
                continue
            
            try:
                stocks.append({
                    'name': row[0],
                    'symbol': row[1],
                    'sector': row[2],
                    'industry': row[3],
                    'cmp': float(row[6]),
                    'trigger': float(row[7]),
                    'condition': row[8]
                })
            except ValueError:
                continue
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

⏰ {datetime.datetime.now().strftime('%d %b %Y, %H:%M:%S')}"""
    
    bot = telebot.Bot(BOT_TOKEN)
    bot.send_message(BOT_CHAT_ID, message, parse_mode='Markdown')

def monitor_stocks():
    print(f"\n🔍 Checking stocks at {datetime.datetime.now()}...")
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
