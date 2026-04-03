import sqlite3
import yfinance as yf
import pandas as pd
import ta
import requests
import time
from datetime import datetime

# ---------------- CONFIG ----------------
TOKEN = "8778308838:AAHrxgW-TPJjqYKvGRXS_mnWaF_uQtn37HE"
CHAT_ID = "510092657"
CAPITAL = 10000
RISK = 0.01

stocks = ["RELIANCE.NS","HDFCBANK.NS","ICICIBANK.NS"]

# ---------------- DB SETUP ----------------
conn = sqlite3.connect("trades.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock TEXT,
    entry REAL,
    sl REAL,
    target REAL,
    qty INTEGER,
    status TEXT,
    profit REAL,
    date TEXT
)
""")
conn.commit()

# ---------------- TELEGRAM ----------------
def send(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# ---------------- LOGIC ----------------
def detect_fvg(df):
    return df['High'].iloc[-3] < df['Low'].iloc[-1]

def liquidity(df):
    return df['Low'].iloc[-1] < df['Low'].iloc[-3] and df['Close'].iloc[-1] > df['Low'].iloc[-3]

def bos(df):
    return df['Close'].iloc[-1] > df['High'].iloc[-2]

def get_market():
    nifty = yf.download("^NSEI", interval="15m", period="1d")
    nifty['ema20'] = ta.trend.ema_indicator(nifty['Close'], 20)
    nifty['ema50'] = ta.trend.ema_indicator(nifty['Close'], 50)

    last = nifty.iloc[-1]
    if last['Close'] > last['ema20'] > last['ema50']:
        return "BULLISH"
    return "SIDEWAYS"

# ---------------- SIGNAL ----------------
def analyze(stock):
    df = yf.download(stock, interval="5m", period="1d")

    df['ema20'] = ta.trend.ema_indicator(df['Close'], 20)
    df['ema50'] = ta.trend.ema_indicator(df['Close'], 50)
    df['rsi'] = ta.momentum.rsi(df['Close'], 14)
    df['vol_avg'] = df['Volume'].rolling(20).mean()

    last = df.iloc[-1]

    score = 0

    if last['Close'] > last['ema20'] > last['ema50']:
        score += 1
    if 50 < last['rsi'] < 70:
        score += 1
    if last['Volume'] > 1.5 * last['vol_avg']:
        score += 1
    if liquidity(df):
        score += 2
    if bos(df):
        score += 2
    if detect_fvg(df):
        score += 2

    if score >= 8:
        entry = last['Close']
        sl = df['Low'].iloc[-3]
        target = entry + (entry - sl) * 2

        risk_amt = CAPITAL * RISK
        qty = int(risk_amt / (entry - sl))

        c.execute("INSERT INTO trades (stock,entry,sl,target,qty,status,date) VALUES (?,?,?,?,?,'OPEN',?)",
                  (stock,entry,sl,target,qty,str(datetime.now())))
        conn.commit()

        send(f"""🔥 SIGNAL

{stock}
Entry: {round(entry,2)}
SL: {round(sl,2)}
Target: {round(target,2)}
Qty: {qty}
""")

# ---------------- TRACK RESULT ----------------
def update_trades():
    c.execute("SELECT * FROM trades WHERE status='OPEN'")
    rows = c.fetchall()

    for row in rows:
        id, stock, entry, sl, target, qty, status, profit, date = row

        df = yf.download(stock, interval="5m", period="1d")
        price = df['Close'].iloc[-1]

        if price >= target:
            pnl = (target - entry) * qty
            c.execute("UPDATE trades SET status='WIN', profit=? WHERE id=?", (pnl,id))
            send(f"🎯 TARGET HIT: {stock} Profit ₹{round(pnl,2)}")

        elif price <= sl:
            pnl = (sl - entry) * qty
            c.execute("UPDATE trades SET status='LOSS', profit=? WHERE id=?", (pnl,id))
            send(f"❌ SL HIT: {stock} Loss ₹{round(pnl,2)}")

    conn.commit()

# ---------------- DAILY REPORT ----------------
def daily_report():
    today = datetime.now().date()
    c.execute("SELECT status, profit FROM trades WHERE date LIKE ?", (f"{today}%",))
    rows = c.fetchall()

    total = len(rows)
    wins = sum(1 for r in rows if r[0]=='WIN')
    pnl = sum(r[1] or 0 for r in rows)

    winrate = (wins/total*100) if total else 0

    send(f"""📊 DAILY REPORT

Trades: {total}
Wins: {wins}
Win Rate: {round(winrate,2)}%
PnL: ₹{round(pnl,2)}
""")

# ---------------- BEST STOCKS ----------------
def best_stocks():
    c.execute("""
    SELECT stock, COUNT(*), SUM(profit)
    FROM trades
    WHERE status='WIN'
    GROUP BY stock
    ORDER BY SUM(profit) DESC
    LIMIT 3
    """)
    rows = c.fetchall()

    msg = "🏆 BEST STOCKS:\n"
    for r in rows:
        msg += f"{r[0]} → Profit ₹{round(r[2],2)}\n"

    send(msg)

# ---------------- LOOP ----------------
while True:
    if get_market() == "BULLISH":
        for s in stocks:
            analyze(s)

    update_trades()

    if datetime.now().hour == 15 and datetime.now().minute == 15:
        daily_report()
        best_stocks()

    time.sleep(300)
