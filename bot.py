import os
import yfinance as yf
import ta
import requests
import time
import threading
from datetime import datetime
from flask import Flask

# -------- FLASK APP --------
app = Flask(__name__)

@app.route('/')
def home():
    return "Trading Bot is Running ✅"

# -------- TELEGRAM --------
TOKEN = os.getenv("8778308838:AAHrxgW-TPJjqYKvGRXS_mnWaF_uQtn37HE")
CHAT_ID = os.getenv("510092657")

def send(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# -------- STOCK LIST --------
stocks = ["RELIANCE.NS","HDFCBANK.NS","ICICIBANK.NS"]

# -------- MARKET TIME --------
def market_open():
    now = datetime.now()
    return now.hour >= 9 and now.hour < 15

# -------- MARKET TREND --------
def market_trend():
    df = yf.download("^NSEI", interval="15m", period="1d")
    df['ema20'] = ta.trend.ema_indicator(df['Close'], 20)
    df['ema50'] = ta.trend.ema_indicator(df['Close'], 50)

    last = df.iloc[-1]

    if last['Close'] > last['ema20'] > last['ema50']:
        return "BULLISH"
    elif last['Close'] < last['ema20'] < last['ema50']:
        return "BEARISH"
    else:
        return "SIDEWAYS"

# -------- SIGNAL LOGIC --------
def analyze(stock, trend):
    try:
        df = yf.download(stock, interval="5m", period="1d")

        df['ema20'] = ta.trend.ema_indicator(df['Close'], 20)
        df['ema50'] = ta.trend.ema_indicator(df['Close'], 50)
        df['rsi'] = ta.momentum.rsi(df['Close'], 14)
        df['vol_avg'] = df['Volume'].rolling(20).mean()

        last = df.iloc[-1]
        prev = df.iloc[-2]

        buy = (
            trend == "BULLISH" and
            last['Close'] > last['ema20'] > last['ema50'] and
            50 < last['rsi'] < 70 and
            last['Volume'] > 1.5 * last['vol_avg'] and
            last['Close'] > prev['High']
        )

        sell = (
            trend == "BEARISH" and
            last['Close'] < last['ema20'] < last['ema50'] and
            30 < last['rsi'] < 50 and
            last['Volume'] > 1.5 * last['vol_avg'] and
            last['Close'] < prev['Low']
        )

        if buy:
            entry = last['Close']
            sl = prev['Low']
            target = entry + (entry - sl) * 2

            send(f"""🚀 BUY SIGNAL

Stock: {stock}
Entry: {round(entry,2)}
SL: {round(sl,2)}
Target: {round(target,2)}

Trend: {trend}
""")

        elif sell:
            entry = last['Close']
            sl = prev['High']
            target = entry - (sl - entry) * 2

            send(f"""🔻 SELL SIGNAL

Stock: {stock}
Entry: {round(entry,2)}
SL: {round(sl,2)}
Target: {round(target,2)}

Trend: {trend}
""")

    except Exception as e:
        print(f"Error in {stock}: {e}")

# -------- MAIN BOT LOOP --------
def run_bot():
    while True:
        try:
            print("Bot running...")

            if market_open():
                trend = market_trend()

                if trend != "SIDEWAYS":
                    for s in stocks:
                        analyze(s, trend)

            time.sleep(300)

        except Exception as e:
            print("Main loop error:", e)
            time.sleep(60)

# -------- START THREAD --------
threading.Thread(target=run_bot).start()

# -------- RUN FLASK --------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
