#!/usr/bin/env python3
"""
Telegram Daily Briefing
Sends daily schedule summary to Telegram
"""

import os
import sqlite3
import requests
from datetime import datetime, timedelta
from typing import List, Dict

class TelegramBriefing:
    def __init__(self, db_path: str, bot_token: str, chat_id: str):
        self.db_path = db_path
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}"

    def send_message(self, text: str):
        """Send message to Telegram"""
        url = f"{self.api_url}/sendMessage"
        payload = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            print("✅ Telegram message sent successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to send Telegram message: {e}")
            return False

    def generate_daily_brief(self, date: str = None) -> str:
        """Generate daily briefing text"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        date_obj = datetime.strptime(date, '%Y-%m-%d')
        day_name = ['월', '화', '수', '목', '금', '토', '일'][date_obj.weekday()]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get events
        cursor.execute("SELECT * FROM econ_events WHERE date = ? ORDER BY time", (date,))
        econ_events = cursor.fetchall()

        cursor.execute("SELECT * FROM nba_games WHERE date = ? ORDER BY time", (date,))
        nba_games = cursor.fetchall()

        cursor.execute("SELECT * FROM soccer_games WHERE date = ? ORDER BY time", (date,))
        soccer_games = cursor.fetchall()

        conn.close()

        # Build message
        msg = "━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"📅 <b>G9 Daily — {date} ({day_name})</b>\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━\n\n"

        # ECON Events
        msg += "📊 <b>ECON</b>\n"
        if econ_events:
            for event in econ_events:
                impact_emoji = {'HIGH': '🔴', 'MID': '🟡', 'LOW': '⚪'}.get(event[4], '')
                msg += f"└─ {impact_emoji} {event[3]} ({event[2]})\n"
        else:
            msg += "└─ No events\n"
        msg += "\n"

        # NBA Games (show all)
        msg += f"🏀 <b>NBA ({len(nba_games)}경기)</b>\n"
        if nba_games:
            for i, game in enumerate(nba_games):
                prefix = "└─" if i == len(nba_games) - 1 else "├─"
                msg += f"{prefix} {game[4]} @ {game[3]} ({game[2]})\n"
        else:
            msg += "└─ No games\n"
        msg += "\n"

        # Soccer Games
        msg += f"⚽ <b>SOCCER ({len(soccer_games)}경기)</b>\n"
        if soccer_games:
            high_games = [g for g in soccer_games if g[6] == 'HIGH']
            if high_games:
                for game in high_games[:3]:
                    msg += f"├─ 🔥 [{game[3]}] {game[4]} vs {game[5]} ({game[2]})\n"
                if len(soccer_games) > 3:
                    msg += f"└─ ... {len(soccer_games) - 3} more\n"
            else:
                for game in soccer_games[:3]:
                    msg += f"├─ [{game[3]}] {game[4]} vs {game[5]} ({game[2]})\n"
                if len(soccer_games) > 3:
                    msg += f"└─ ... {len(soccer_games) - 3} more\n"
        else:
            msg += "└─ No matches\n"
        msg += "\n"

        # My Tasks (Fixed schedule based on weekday)
        msg += "━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "⏰ <b>내 작업</b>\n"

        is_weekend = date_obj.weekday() >= 5  # Sat=5, Sun=6
        tasks = []

        if is_weekend:
            # Weekend schedule
            if soccer_games:
                tasks.append("├─ 06:30 SOCCER 검토 ⚽")
            tasks.append("├─ 07:00 ECON Asia 검토")
            if nba_games:
                tasks.append("├─ 20:00 NBA 검토 🏀")
            tasks.append("└─ 20:30 ECON US 검토")
        else:
            # Weekday schedule
            tasks.append("├─ 06:30 ECON Asia 검토")
            if nba_games:
                tasks.append("├─ 20:00 NBA 검토 🏀")
            tasks.append("└─ 20:30 ECON US 검토")

        msg += '\n'.join(tasks) + '\n'

        # Warnings for HIGH impact events
        high_econ = [e for e in econ_events if e[4] == 'HIGH']
        if high_econ:
            msg += f"\n🔴 <b>빅 이벤트:</b> {high_econ[0][3]} ({high_econ[0][2]})\n"
            msg += "⚠️ 변동성 주의\n"

        msg += "━━━━━━━━━━━━━━━━━━━━━━"

        return msg

    def send_daily_brief(self, date: str = None):
        """Generate and send daily briefing"""
        msg = self.generate_daily_brief(date)
        return self.send_message(msg)

    def get_chat_id(self):
        """Helper: Get chat ID for the bot"""
        url = f"{self.api_url}/getUpdates"
        try:
            response = requests.get(url, timeout=10)
            data = response.json()
            if data.get('result'):
                for update in data['result']:
                    if 'message' in update:
                        chat_id = update['message']['chat']['id']
                        print(f"Chat ID: {chat_id}")
                        return chat_id
            print("No messages found. Send a message to the bot first.")
        except Exception as e:
            print(f"Error: {e}")
        return None

# CLI usage
if __name__ == '__main__':
    import sys
    from dotenv import load_dotenv
    load_dotenv()

    db_path = os.getenv('DB_PATH')
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env")
        sys.exit(1)

    briefing = TelegramBriefing(db_path, bot_token, chat_id)

    if len(sys.argv) > 1:
        if sys.argv[1] == 'getchat':
            # Get chat ID
            briefing.get_chat_id()
        else:
            # Send briefing for specific date
            date = sys.argv[1]
            briefing.send_daily_brief(date)
    else:
        if not chat_id:
            print("❌ TELEGRAM_CHAT_ID not set. Run with 'getchat' to find it:")
            print("   python telegram_briefing.py getchat")
            sys.exit(1)

        # Send today's briefing
        briefing.send_daily_brief()
