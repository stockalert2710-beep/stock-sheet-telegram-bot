Python 3.13.14 (tags/v3.13.14:fd17997, Jun 10 2026, 13:03:48) [MSC v.1944 64 bit (AMD64)] on win32
Enter "help" below or click "Help" above for more information.
>>> # -*- coding: utf-8 -*-
... import gspread
... from oauth2client.service_account import ServiceAccountCredentials
... from telebot import TeleBot
... import yfinance as yf
... import schedule
... import time
... import datetime
... 
... # ===== CONFIGURATION =====
... # Google Sheets
... SERVICE_ACCOUNT_FILE = 'C:\Users\jaina\OneDrive\Desktop\stock_bot_folder\service_account.json'  # Path to your JSON file
... SPREADSHEET_NAME = 'StockAlert'  # Your Google Sheet name
... SHEET_NAME = 'Sheet1'  # Default sheet name (change if different)
... 
... # Telegram
... BOT_TOKEN = '8988067878:AAHk4G1XsUicBOtfoG_yfLugt9uhtuYus9k'  # From BotFather
... BOT_CHAT_ID = 'StockSheetAlertBot'  # Your Telegram user ID
... 
... # ===== CONNECT TO GOOGLE SHEETS =====
... def connect_to_sheets():
...     """Connect to Google Sheets using service account"""
...     try:
...         gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
...         sh = gc.open(SPREADSHEET_NAME)
...         sheet = sh.sheet1
...         return sheet
...     except Exception as e:
...         print(f"Error connecting to Sheets: {e}")
...         return None
... 
... # ===== READ DATA FROM SHEET =====
... def read_sheet_data():
...     """Read stock data from Google Sheet"""
...     sheet = connect_to_sheets()
...     if sheet is None:
...         return []
...     
...     # Get all data
...     data = sheet.get_all_values()
...     
...     if len(data) < 2:  # Less than 1 row of data
...         return []
...     
...     # Parse headers and data
    headers = data[0]  # Row 1: Headers
    rows = data[1:]    # Row 2+: Data
    
    stocks = []
    for row in rows:
        if len(row) >= 9:  # Ensure at least 9 columns
            stock = {
                'name': row[0],       # Column A
                'symbol': row[1],     # Column B
                'sector': row[2],     # Column C
                'industry': row[3],   # Column D
                'iso_code': row[4],   # Column E
                'expiry': row[5],     # Column F
                'cmp': row[6],        # Column G (CMP)
                'trigger': row[7],    # Column H (Trigger)
                'condition': row[8]   # Column I (Condition)
            }
            stocks.append(stock)
    
    return stocks

# ===== GET LIVE PRICES =====
# Column G (CMP)
# Column H (Trigger)
# Column I (Condition: more than / less than)
def get_live_price(symbol):
    """Get current price from Yahoo Finance"""
    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period='1d')
        if len(data) > 0:
            return data['Close'].iloc[-1]
        return None
    except:
        return None

# ===== CHECK IF ALERT TRIGGERED =====
def check_alert_triggered(cmp, trigger, condition):
    """Check if alert should be sent"""
    if condition == 'more than':
        return cmp >= trigger
    elif condition == 'less than':
        return cmp <= trigger
    return False

# ===== SEND TELEGRAM MESSAGE =====
def send_telegram_alert(stock_name, symbol, cmp, trigger, condition, sector, industry, expiry):
    """Send formatted alert to Telegram"""
    
    # Format message
    if condition == 'more than':
        emoji = '🚨'
        status = 'Price ≥ Trigger ✅'
    else:
        emoji = '🔻'
        status = 'Price ≤ Trigger ✅'
    
    message = f"""{emoji} **ALERT TRIGGERED!** {emoji}

📊 **Stock Details:**
• Name: {stock_name}
• Symbol: {symbol}
• Sector: {sector}
• Industry: {industry}
• Expiry: {expiry}

💰 **Price Alert:**
• Current Price (CMP): ₹{cmp:.2f}
• Trigger Price: ₹{trigger}
• Condition: {condition}
• Status: {status}

⏰ Time: {datetime.now().strftime('%d %b %Y, %H:%M:%S')}"""

    # Send via Telegram
    try:
        bot = TeleBot(BOT_TOKEN)
        bot.send_message(BOT_CHAT_ID, message, parse_mode='Markdown')
        print(f"✓ Alert sent for {stock_name}")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

# ===== MONITOR ALL STOCKS FROM SHEET =====
def monitor_stocks_from_sheet():
    """Main function to check all stocks in Google Sheet"""
    print(f"\n🔍 Checking stocks at {datetime.now().strftime('%H:%M:%S')}...")
    
    # Read data from Google Sheet
    stocks = read_sheet_data()
    
    if len(stocks) == 0:
        print("No stocks found in sheet")
        return
    
    print(f"Monitoring {len(stocks)} stocks...")
    
    alerts_sent = []
    
    for stock in stocks:
        try:
            # Get live price
            live_price = get_live_price(stock['symbol'])
            
            if live_price is None:
                print(f"✗ {stock['name']}: Price unavailable")
                continue
            
            # Convert to float
            cmp = float(live_price)
            trigger = float(stock['trigger'])
            
            # Check if alert triggered
            if check_alert_triggered(cmp, trigger, stock['condition']):
                # Send Telegram alert
                send_telegram_alert(
                    stock_name=stock['name'],
                    symbol=stock['symbol'],
                    cmp=cmp,
                    trigger=trigger,
                    condition=stock['condition'],
                    sector=stock['sector'],
                    industry=stock['industry'],
                    expiry=stock['expiry']
                )
                alerts_sent.append(stock['name'])
            else:
                print(f"✓ {stock['name']}: ₹{cmp:.2f} (Trigger: ₹{trigger}, {stock['condition']})")
        
        except Exception as e:
            print(f"✗ Error processing {stock['name']}: {e}")
    
    # Summary
    if alerts_sent:
        print(f"\n🎉 Alerts sent: {len(alerts_sent)}")
    else:
        print(f"\n✓ No alerts triggered")

# ===== SCHEDULE: CHECK EVERY 5 MINUTES =====
schedule.every(5).minutes.do(monitor_stocks_from_sheet)

# ===== START MONITORING =====
if __name__ == "__main__":
    print("🚀 Google Sheets + Telegram Stock Alert Bot Started!")
    print(f"📊 Monitoring: {SPREADSHEET_NAME}")
    print(f"⏰ Check interval: Every 5 minutes")
    print(f"📱 Telegram: {BOT_CHAT_ID}")
    print("\nPress Ctrl+C to stop\n")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
