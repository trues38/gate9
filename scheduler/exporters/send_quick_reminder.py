#!/usr/bin/env python3
"""
Quick task reminder - sends simple notification
"""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

if len(sys.argv) < 2:
    print("Usage: send_quick_reminder.py <task_description>")
    sys.exit(1)

task = sys.argv[1]

message = f"⏰ <b>30분 뒤</b>\n└─ {task}"

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
payload = {
    'chat_id': CHAT_ID,
    'text': message,
    'parse_mode': 'HTML'
}

try:
    response = requests.post(url, json=payload, timeout=10)
    response.raise_for_status()
    print(f"✅ Reminder sent: {task}")
except Exception as e:
    print(f"❌ Failed: {e}")
