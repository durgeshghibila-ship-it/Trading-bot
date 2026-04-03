import os
import yfinance as yf
import ta
import requests
import time

TOKEN = os.getenv("8778308838:AAHrxgW-TPJjqYKvGRXS_mnWaF_uQtn37HE")
CHAT_ID = os.getenv("510092657")

stocks = ["RELIANCE.NS","HDFCBANK.NS","ICICIBANK.NS"]

def send(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

def analyze(stock):
    try:
        df = yf.download(stock, interval="5m", period="1d")

        df['ema20'] = ta.trend.ema_indicator(df['Close'], 20)
        df['ema50'] = ta.trend.ema_indicator(df['Close'], 50)
        df['rsi'] = ta.momentum.rsi(df['Close'], 14)
        df['vol_avg'] = df['Volume'].rolling(20).mean()

        last = df.iloc[-1]
        prev = df.iloc[-2]

        # Conditions
        trend = last['Close'] > last['ema20'] > last['ema50']
        rsi_ok = 50 < last['rsi'] < 70
        volume_ok = last['Volume'] > 1.5 * last['vol_avg']
        breakout = last['Close'] > prev['High']

        if trend and rsi_ok and volume_ok and breakout:
            entry = last['Close']
            sl = prev['Low']
            target = entry + (entry - sl) * 2

            msg = f"""🔥 SIGNAL

Stock: {stock}
Entry: {round(entry,2)}
SL: {round(sl,2)}
Target: {round(target,2)}

✔ EMA Trend
✔ RSI Momentum
✔ Volume Spike
✔ Breakout
"""
            send(msg)

    except Exception as e:
        print(e)

while True:
    for s in stocks:
        analyze(s)
    time.sleep(300)
