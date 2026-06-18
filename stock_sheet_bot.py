# -*- coding: utf-8 -*-
import gspread
from google.oauth2 import service_account
import telebot
import yfinance as yf
import datetime
import time
import json
import schedule
import pytz
from flask import Flask, request

# Set timezone to IST
ist = pytz.timezone('Asia/Kolkata')

# Your credentials (hardcoded for Uptime Robot)
SERVICE_ACCOUNT_JSON = """
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "your-key-id",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "your-email@your-project.iam.gserviceaccount.com",
  "client_id": "your-client-id",
  "auth_uri": "https://accounts.google.com/o/oauth2",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://...",
  "universe_domain": "googleapis.com"
}
"""

SPREADSHEET_ID = '1Fq8dKl_72XqdrAcA6atIl5kD23lnkYKSzH4wVNCyQUs'
BOT_TOKEN = '8988067878:AAHk4G1XsUicBOtfoG_yfLugt9uhtuYus9k'
BOT_CHAT_ID = '615256683'

# Flask app
app = Flask(__name__)


def is_trading_hours():
    """
    Check if current time is within Indian trading hours:
    9:00 AM - 3:30 PM IST, Monday to Friday
    """
    now_ist = datetime.datetime.now(ist)
    current_time = now_ist.time()
    current_day = now_ist.weekday()  # 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
    
    # Trading hours: 9:00 AM to 3:30 PM
    start_time = datetime.time(9, 0, 0)
    end_time = datetime.time(15, 30, 0)
    
    # Monday to Friday (0-4)
    is_weekday = current_day <= 4
    is_within_hours = start_time <= current_time <= end_time
    
    return is_weekday and is_within_hours


def get_ist_time():
    """Get current time in IST format"""
    return datetime.datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S IST')


def connect_to_sheets():
    """Connect to Google Sheets"""
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
    return sh.sheet1


def read_sheet_data():
    """Read stock data from Google Sheet - Optimized"""
    sheet = connect_to_sheets()
    data = sheet.get_all_values()
    
    if len(data) < 2:
        return []
    
    stocks = []
    for row in data[1:]:
        # Skip invalid rows quickly
        if len(row) < 13 or row[8] == '':
            continue
        
        try:
            stocks.append({
                'name': row[1],
                'ID': row[3],
                'trigger': float(row[8]),
                'remarks': row[12]
            })
        except ValueError:
            continue
    
    return stocks


def get_live_price(symbol):
    """Get live price from Yahoo Finance - Optimized"""
    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period='1d', interval='1m')
        return data['Close'].iloc[-1] if len(data) > 0 else None
    except:
        return None


def send_telegram_alert(stock, current_price):
    """Send Telegram alert"""
    try:
        message = f"""🚨 ALERT! 🚨

Stock: {stock['name']} ({stock['ID']})
Trigger: ₹{stock['trigger']}
Current: ₹{current_price:.2f}
Remarks: {stock['remarks']}"""
        
        bot = telebot.TeleBot(BOT_TOKEN)
        bot.send_message(BOT_CHAT_ID, message)
        print(f"✅ Alert: {stock['name']} at {get_ist_time()}")
    except Exception as e:
        print(f"❌ Telegram error: {e}")


def monitor_stocks():
    """Main function - Optimized & with trading hours check"""
    print(f"\n⏰ Stock check at {get_ist_time()}")
    
    stocks = read_sheet_data()
    print(f"📊 Stocks: {len(stocks)}")
    
    if len(stocks) == 0:
        print("No stocks")
        return
    
    for stock in stocks:
        price = get_live_price(stock['ID'])
        
        if price:
            if price >= stock['trigger']:
                # Only send if within trading hours (9 AM - 3:30 PM IST, Mon-Fri)
                if is_trading_hours():
                    send_telegram_alert(stock, price)
                else:
                    print(f"⏸️ Skipped: {stock['name']} (outside trading hours)")
            else:
                print(f"✓ {stock['name']}: ₹{price:.2f}")
        else:
            print(f"⚠️ No data: {stock['name']}")
    
    print(f"✅ Completed at {get_ist_time()}\n")


def run_periodically():
    """Run every 15 minutes for Uptime Robot"""
    print("🔄 Starting periodic monitor (15 min)")
    
    # Run immediately
    monitor_stocks()
    
    # Schedule every 15 minutes
    schedule.every(15).minutes.do(monitor_stocks)
    
    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(1)


# Flask Routes
@app.route("/")
def home():
    return "Server is running ✓"


@app.route("/run")
def run():
    key = request.args.get("key")
    
    if key != "secret123":
        return "Unauthorized", 403
    
    monitor_stocks()
    return "Script executed ✓"


if __name__ == "__main__":
    # For Uptime Robot: Run periodically
    run_periodically()
