#!/usr/bin/env python3
"""
G9 Schedule Manager — Main Orchestrator
Coordinates all collectors and exporters
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from collectors.nba_collector import NBACollector
from collectors.soccer_collector import SoccerCollector
from collectors.econ_collector import EconCollector
from exporters.sheets_exporter import SheetsExporter
from exporters.calendar_exporter import CalendarExporter
from exporters.md_exporter import MDExporter
from exporters.telegram_briefing import TelegramBriefing

class ScheduleManager:
    def __init__(self):
        load_dotenv()

        self.db_path = os.getenv('DB_PATH')
        self.output_dir = os.getenv('OUTPUT_DIR')

        # API Keys
        self.football_api_key = os.getenv('FOOTBALL_API_KEY')
        self.fred_api_key = os.getenv('FRED_API_KEY')

        # Google credentials
        self.google_creds = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
        self.google_sheet_id = os.getenv('GOOGLE_SHEET_ID')
        self.google_calendar_id = os.getenv('GOOGLE_CALENDAR_ID', 'primary')

        # Telegram
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')

        # Initialize components
        self.nba_collector = NBACollector(self.db_path)
        self.soccer_collector = SoccerCollector(self.db_path, self.football_api_key)
        self.econ_collector = EconCollector(self.db_path, self.fred_api_key)

        self.md_exporter = MDExporter(self.db_path, self.output_dir)

        # Google exporters (may be None if credentials not set)
        try:
            if self.google_creds and os.path.exists(self.google_creds):
                self.sheets_exporter = SheetsExporter(self.db_path, self.google_creds, self.google_sheet_id)
                self.calendar_exporter = CalendarExporter(self.db_path, self.google_creds, self.google_calendar_id)
            else:
                print("⚠️  Google credentials not found - Sheets/Calendar export disabled")
                self.sheets_exporter = None
                self.calendar_exporter = None
        except Exception as e:
            print(f"⚠️  Google services initialization failed: {e}")
            self.sheets_exporter = None
            self.calendar_exporter = None

        # Telegram (may be None if not configured)
        if self.telegram_bot_token and self.telegram_chat_id:
            self.telegram = TelegramBriefing(self.db_path, self.telegram_bot_token, self.telegram_chat_id)
        else:
            print("⚠️  Telegram not configured - Daily briefing disabled")
            self.telegram = None

    def collect_month(self, year: int, month: int):
        """Collect all schedules for a specific month"""
        print(f"\n{'='*60}")
        print(f"📅 Collecting schedules for {year}-{month:02d}")
        print(f"{'='*60}\n")

        # Collect NBA
        print("🏀 Collecting NBA games...")
        nba_games = self.nba_collector.fetch_month(year, month)
        if nba_games:
            self.nba_collector.save_to_db(nba_games)

        # Collect Soccer
        print("\n⚽ Collecting Soccer matches...")
        soccer_games = self.soccer_collector.fetch_month(year, month)
        if soccer_games:
            self.soccer_collector.save_to_db(soccer_games)

        # Collect ECON
        print("\n📊 Collecting ECON events...")
        econ_events = self.econ_collector.collect_and_save(year, month)

        print(f"\n{'='*60}")
        print(f"✅ Collection complete!")
        print(f"   NBA: {len(nba_games)} games")
        print(f"   Soccer: {len(soccer_games)} matches")
        print(f"   ECON: {len(econ_events)} events")
        print(f"{'='*60}\n")

    def export_month(self, year: int, month: int):
        """Export schedules to all platforms"""
        print(f"\n{'='*60}")
        print(f"📤 Exporting schedules for {year}-{month:02d}")
        print(f"{'='*60}\n")

        # Export to MD files
        print("📝 Exporting to MD files...")
        self.md_exporter.export_monthly_schedule(year, month)

        # Export to Google Sheets
        if self.sheets_exporter:
            print("\n📊 Exporting to Google Sheets...")
            self.sheets_exporter.export_month(year, month)
        else:
            print("\n⚠️  Google Sheets export skipped (not configured)")

        # Export to Google Calendar
        if self.calendar_exporter:
            print("\n📅 Exporting to Google Calendar...")
            self.calendar_exporter.export_month(year, month)
        else:
            print("\n⚠️  Google Calendar export skipped (not configured)")

        print(f"\n{'='*60}")
        print(f"✅ Export complete!")
        print(f"{'='*60}\n")

    def send_daily_brief(self, date: str = None):
        """Send daily briefing via Telegram"""
        if not self.telegram:
            print("❌ Telegram not configured")
            return

        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        print(f"📱 Sending daily briefing for {date}...")
        success = self.telegram.send_daily_brief(date)

        if success:
            print("✅ Daily briefing sent!")
        else:
            print("❌ Failed to send daily briefing")

    def run_monthly_collection(self):
        """
        Monthly collection job
        Runs on 25th of each month to prepare next month
        """
        today = datetime.now()
        next_month = today + timedelta(days=7)  # Next month

        year = next_month.year
        month = next_month.month

        print(f"🔄 Running monthly collection job for {year}-{month:02d}")

        self.collect_month(year, month)
        self.export_month(year, month)

        print("✅ Monthly collection job complete!")

    def run_daily_brief(self):
        """
        Daily briefing job
        Runs every morning at 06:30 KST
        """
        today = datetime.now().strftime('%Y-%m-%d')

        print(f"🔄 Running daily briefing job for {today}")

        # Also export daily MD file
        self.md_exporter.export_daily_schedule(today)

        # Send Telegram briefing
        self.send_daily_brief(today)

        print("✅ Daily briefing job complete!")

    def run_weekly_preview(self):
        """
        Weekly preview job
        Runs every Sunday evening
        """
        today = datetime.now()
        week = today.isocalendar()[1]

        print(f"🔄 Running weekly preview for week {week}")

        # Export weekly MD
        self.md_exporter.export_weekly_schedule(today.year, week + 1)

        print("✅ Weekly preview complete!")

# CLI Interface
def main():
    manager = ScheduleManager()

    if len(sys.argv) < 2:
        print("G9 Schedule Manager")
        print("\nUsage:")
        print("  python schedule_manager.py collect <year> <month>   # Collect schedules")
        print("  python schedule_manager.py export <year> <month>    # Export schedules")
        print("  python schedule_manager.py brief [date]             # Send daily brief")
        print("  python schedule_manager.py monthly                  # Run monthly job")
        print("  python schedule_manager.py daily                    # Run daily job")
        print("  python schedule_manager.py weekly                   # Run weekly job")
        sys.exit(0)

    command = sys.argv[1]

    if command == 'collect':
        if len(sys.argv) < 4:
            print("Usage: python schedule_manager.py collect <year> <month>")
            sys.exit(1)
        year = int(sys.argv[2])
        month = int(sys.argv[3])
        manager.collect_month(year, month)

    elif command == 'export':
        if len(sys.argv) < 4:
            print("Usage: python schedule_manager.py export <year> <month>")
            sys.exit(1)
        year = int(sys.argv[2])
        month = int(sys.argv[3])
        manager.export_month(year, month)

    elif command == 'brief':
        date = sys.argv[2] if len(sys.argv) > 2 else None
        manager.send_daily_brief(date)

    elif command == 'monthly':
        manager.run_monthly_collection()

    elif command == 'daily':
        manager.run_daily_brief()

    elif command == 'weekly':
        manager.run_weekly_preview()

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == '__main__':
    main()
