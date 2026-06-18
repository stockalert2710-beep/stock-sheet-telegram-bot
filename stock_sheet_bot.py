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
BOT_TOKEN = '8988067878:AAHk4G1XsUicBOtfoG_yfLugt9uhtuYus9k'
BOT_CHAT_ID = 'StockSheetAlertBot'  # Replace with your chat ID number

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
        if len(row) >= 12:
            # Skip rows with empty Trigger (column H = index 7)
            if row[7] == '':
                continue
            
            try:
                stocks.append({
                    'name': row[1],           # B: Name
                    'exchange': row[2],       # C: Exchange
                    'ID': row[3],             # D: ID
                    'elliot_position': row[4], # E: Elliot position
                    'price_bo': row[5],        # F: Price BO?
                    'rsi_bo': row[6],          # G: RSI BO
                    'trigger': float(row[7]),  # H: Trigger
                    'buying_zone': row[8],     # I: Buying zone
                    'SL': row[9],              # J: SL
                    'T&T': row[10],            # K: T&T
                    'remarks': row[11]         # L: Remarks
                })
            except ValueError:
                continue
                print (stocks)
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

def check_alert_triggered(cmp, trigger):
    return cmp >= trigger

def send_telegram_alert(stock):
    message = f"""🚨 **ALERT TRIGGERED!** 🚨

📊 Stock: {stock['name']}
Exchange: {stock['exchange']}
ID: {stock['ID']}

💰 Price Alert:
• Trigger: ₹{stock['trigger']}
• Buying Zone: {stock['buying_zone']}
• SL: {stock['SL']}
• T&T: {stock['T&T']}

📝 Remarks: {stock['remarks']}

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
        # Use ID as symbol for yfinance
        live_price = get_live_price(stock['ID'])
        if live_price:
            if check_alert_triggered(live_price, stock['trigger']):
                send_telegram_alert(stock)
                print(f"✓ Alert sent for {stock['name']}")
            else:
                print(f"✓ {stock['name']}: ₹{live_price:.2f} (Trigger: ₹{stock['trigger']})")

if __name__ == "__main__":
    monitor_stocks()
