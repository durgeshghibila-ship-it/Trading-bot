import os
import requests
import time

TOKEN = os.getenv("8778308838:AAHrxgW-TPJjqYKvGRXS_mnWaF_uQtn37HE")
CHAT_ID = os.getenv("510092657")

def send(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

while True:
    send("Bot is running ✅")
    time.sleep(60)
