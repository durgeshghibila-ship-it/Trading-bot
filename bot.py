import os
import yfinance as yf
import ta
import requests
import time
import threading
from datetime import datetime
from flask import Flask

# -------- FLASK --------
app = Flask(__name__)

@app.route('/')
def home():
    return "Ultimate Trading Bot Running ✅"

# -------- TELEGRAM --------
TOKEN = os.getenv("8778308838:AAHrxgW-TPJjqYKvGRXS_mnWaF_uQtn37HE")
CHAT_ID = os.getenv("510092657")

def send(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# -------- NIFTY STOCK LIST --------
stocks = [
"RELIANCE.NS","HDFCBANK.NS","ICICIBANK.NS","INFY.NS","TCS.NS",
"SBIN.NS","AXISBANK.NS","KOTAKBANK.NS","LT.NS","ITC.NS",
"BHARTIARTL.NS","ASIANPAINT.NS","HINDUNILVR.NS","MARUTI.NS",
"TITAN.NS","SUNPHARMA.NS","ULTRACEMCO.NS","NTPC.NS",
"POWERGRID.NS","ONGC.NS","BAJFINANCE.NS","HCLTECH.NS",
"WIPRO.NS","ADANIENT.NS","TATAMOTORS.NS"
]

# -------- MARKET TIME --------
def market_open():
    now = datetime.now()
    return now.hour >= 9 and now.hour < 15

# -------- MARKET TREND (NIFTY) --------
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

# -------- MAIN ANALYSIS (SMC + SMART FILTER) --------
def analyze(stock, trend):
    try:
        df = yf.download(stock, interval="5m", period="1d")

        df['ema20'] = ta.trend.ema_indicator(df['Close'], 20)
        df['ema50'] = ta.trend.ema_indicator(df['Close'], 50)
        df['rsi'] = ta.momentum.rsi(df['Close'], 14)
        df['vol_avg'] = df['Volume'].rolling(20).mean()

        last = df.iloc[-1]
        prev = df.iloc[-2]
        prev2 = df.iloc[-3]

        # -------- SMART FILTER --------
        volume_ok = last['Volume'] > 1.5 * last['vol_avg']
        strong_candle = abs(last['Close'] - last['Open']) > (last['High'] - last['Low']) * 0.6

        if not (volume_ok and strong_candle):
            return

        # -------- SMC LOGIC --------
        liquidity_buy = last['Low'] < prev2['Low'] and last['Close'] > prev2['Low']
        bos_buy = last['Close'] > prev['High']

        liquidity_sell = last['High'] > prev2['High'] and last['Close'] < prev2['High']
        bos_sell = last['Close'] < prev['Low']

        # -------- BUY --------
        buy = (
            trend == "BULLISH" and
            last['Close'] > last['ema20'] > last['ema50'] and
            50 < last['rsi'] < 70 and
            liquidity_buy and
            bos_buy
        )

        # -------- SELL --------
        sell = (
            trend == "BEARISH" and
            last['Close'] < last['ema20'] < last['ema50'] and
            30 < last['rsi'] < 50 and
            liquidity_sell and
            bos_sell
        )

        if buy:
            entry = last['Close']
            sl = prev2['Low']
            target = entry + (entry - sl) * 2

            send(f"""🔥 SMC BUY SIGNAL

Stock: {stock}
Entry: {round(entry,2)}
SL: {round(sl,2)}
Target: {round(target,2)}

✔ Liquidity Sweep
✔ Break of Structure
✔ Trend Confirmed
✔ Volume Strong
""")

        elif sell:
            entry = last['Close']
            sl = prev2['High']
            target = entry - (sl - entry) * 2

            send(f"""🔻 SMC SELL SIGNAL

Stock: {stock}
Entry: {round(entry,2)}
SL: {round(sl,2)}
Target: {round(target,2)}

✔ Liquidity Sweep
✔ Break of Structure
✔ Trend Confirmed
✔ Volume Strong
""")

    except Exception as e:
        print(f"Error in {stock}: {e}")

# -------- BOT LOOP --------
def run_bot():
    while True:
        try:
            print("Scanning market...")

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

# -------- RUN SERVER --------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
