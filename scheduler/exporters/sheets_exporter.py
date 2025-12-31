#!/usr/bin/env python3
"""
Google Sheets Exporter
Creates and updates Google Sheets with schedule data
"""

import os
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict
import gspread
from oauth2client.service_account import ServiceAccountCredentials

class SheetsExporter:
    def __init__(self, db_path: str, credentials_path: str, sheet_id: str = None):
        self.db_path = db_path
        self.sheet_id = sheet_id

        # Authenticate with Google
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]

        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
            self.client = gspread.authorize(creds)
            print("✅ Google Sheets authentication successful")
        except Exception as e:
            print(f"❌ Google Sheets authentication failed: {e}")
            self.client = None

    def get_or_create_sheet(self, title: str = "G9_Schedule_2025"):
        """Get existing sheet or create new one"""
        if not self.client:
            return None

        try:
            if self.sheet_id:
                sheet = self.client.open_by_key(self.sheet_id)
            else:
                sheet = self.client.open(title)
            print(f"✅ Opened existing sheet: {title}")
        except gspread.SpreadsheetNotFound:
            sheet = self.client.create(title)
            print(f"✅ Created new sheet: {title}")
            # Share with yourself (optional)
            # sheet.share('your-email@gmail.com', perm_type='user', role='writer')

        return sheet

    def create_monthly_overview(self, sheet, year: int, month: int):
        """Create Monthly Overview tab"""
        worksheet_name = f"{year}-{month:02d}_Overview"

        # Get or create worksheet
        try:
            worksheet = sheet.worksheet(worksheet_name)
            worksheet.clear()
        except gspread.WorksheetNotFound:
            worksheet = sheet.add_worksheet(title=worksheet_name, rows=50, cols=10)

        # Headers
        headers = ['Date', 'Day', 'ECON', 'NBA', 'SOCCER', 'My Task', 'Note']
        worksheet.update('A1:G1', [headers])

        # Format header
        worksheet.format('A1:G1', {
            'backgroundColor': {'red': 0.2, 'green': 0.2, 'blue': 0.2},
            'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
        })

        # Get data from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        from calendar import monthrange
        days_in_month = monthrange(year, month)[1]

        rows = []
        for day in range(1, days_in_month + 1):
            date_str = f"{year}-{month:02d}-{day:02d}"
            date_obj = datetime(year, month, day)
            day_name = ['월', '화', '수', '목', '금', '토', '일'][date_obj.weekday()]

            # Count events
            cursor.execute("SELECT COUNT(*) FROM econ_events WHERE date = ?", (date_str,))
            econ_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM nba_games WHERE date = ?", (date_str,))
            nba_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM soccer_games WHERE date = ?", (date_str,))
            soccer_count = cursor.fetchone()[0]

            # Check for high-impact ECON events
            cursor.execute("SELECT event_name FROM econ_events WHERE date = ? AND impact = 'HIGH'", (date_str,))
            high_econ = cursor.fetchall()
            econ_display = f"🔴 {high_econ[0][0]}" if high_econ else ('✅' if econ_count > 0 else '')

            # My tasks
            tasks = []
            if econ_count > 0:
                tasks.append('E')
            if nba_count > 0:
                tasks.append('N')
            if soccer_count > 0:
                tasks.append('S')
            my_task = '+'.join(tasks)

            rows.append([
                f"{month}/{day}",
                day_name,
                econ_display,
                nba_count if nba_count > 0 else '',
                soccer_count if soccer_count > 0 else '',
                my_task,
                ''
            ])

        conn.close()

        # Update sheet
        if rows:
            worksheet.update(f'A2:G{len(rows)+1}', rows)

        print(f"✅ Created Monthly Overview for {year}-{month:02d}")

    def create_nba_detail(self, sheet, year: int, month: int):
        """Create NBA Detail tab"""
        worksheet_name = f"{year}-{month:02d}_NBA"

        try:
            worksheet = sheet.worksheet(worksheet_name)
            worksheet.clear()
        except gspread.WorksheetNotFound:
            worksheet = sheet.add_worksheet(title=worksheet_name, rows=200, cols=7)

        # Headers
        headers = ['Date', 'Time', 'Home', 'Away', 'Importance', 'Status', 'Notes']
        worksheet.update('A1:G1', [headers])

        # Format header
        worksheet.format('A1:G1', {
            'backgroundColor': {'red': 0.8, 'green': 0.2, 'blue': 0.2},
            'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
        })

        # Get NBA games from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT date, time, home_team, away_team, importance, status, notes
            FROM nba_games
            WHERE date LIKE ?
            ORDER BY date, time
        """, (f"{year}-{month:02d}%",))

        games = cursor.fetchall()
        conn.close()

        rows = []
        for game in games:
            importance_display = {
                'HIGH': '🔴 HIGH',
                'MID': '🟡 MID',
                'LOW': '⚪ LOW'
            }.get(game[4], game[4])

            rows.append([
                game[0],  # date
                game[1],  # time
                game[2],  # home
                game[3],  # away
                importance_display,
                game[5],  # status
                game[6]   # notes
            ])

        if rows:
            worksheet.update(f'A2:G{len(rows)+1}', rows)

        print(f"✅ Created NBA Detail for {year}-{month:02d} ({len(rows)} games)")

    def create_soccer_detail(self, sheet, year: int, month: int):
        """Create Soccer Detail tab"""
        worksheet_name = f"{year}-{month:02d}_Soccer"

        try:
            worksheet = sheet.worksheet(worksheet_name)
            worksheet.clear()
        except gspread.WorksheetNotFound:
            worksheet = sheet.add_worksheet(title=worksheet_name, rows=200, cols=8)

        # Headers
        headers = ['Date', 'Time', 'League', 'Home', 'Away', 'Importance', 'Status', 'Notes']
        worksheet.update('A1:H1', [headers])

        # Format header
        worksheet.format('A1:H1', {
            'backgroundColor': {'red': 0.2, 'green': 0.8, 'blue': 0.2},
            'textFormat': {'bold': True, 'foregroundColor': {'red': 0, 'green': 0, 'blue': 0}}
        })

        # Get soccer games from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT date, time, league, home_team, away_team, importance, status, notes
            FROM soccer_games
            WHERE date LIKE ?
            ORDER BY date, time
        """, (f"{year}-{month:02d}%",))

        games = cursor.fetchall()
        conn.close()

        rows = []
        for game in games:
            importance_display = {
                'HIGH': '🔴 HIGH',
                'MID': '🟡 MID',
                'LOW': '⚪ LOW'
            }.get(game[5], game[5])

            rows.append([
                game[0],  # date
                game[1],  # time
                game[2],  # league
                game[3],  # home
                game[4],  # away
                importance_display,
                game[6],  # status
                game[7]   # notes
            ])

        if rows:
            worksheet.update(f'A2:H{len(rows)+1}', rows)

        print(f"✅ Created Soccer Detail for {year}-{month:02d} ({len(rows)} games)")

    def create_econ_detail(self, sheet, year: int, month: int):
        """Create ECON Events tab"""
        worksheet_name = f"{year}-{month:02d}_ECON"

        try:
            worksheet = sheet.worksheet(worksheet_name)
            worksheet.clear()
        except gspread.WorksheetNotFound:
            worksheet = sheet.add_worksheet(title=worksheet_name, rows=100, cols=7)

        # Headers
        headers = ['Date', 'Time', 'Event', 'Impact', 'Country', 'Notes', 'Data']
        worksheet.update('A1:G1', [headers])

        # Format header
        worksheet.format('A1:G1', {
            'backgroundColor': {'red': 0.2, 'green': 0.2, 'blue': 0.8},
            'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}}
        })

        # Get econ events from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT date, time, event_name, impact, country, notes, actual, forecast, previous
            FROM econ_events
            WHERE date LIKE ?
            ORDER BY date, time
        """, (f"{year}-{month:02d}%",))

        events = cursor.fetchall()
        conn.close()

        rows = []
        for event in events:
            impact_display = {
                'HIGH': '🔴 HIGH',
                'MID': '🟡 MID',
                'LOW': '⚪ LOW'
            }.get(event[3], event[3])

            data_str = ''
            if event[6]:  # actual
                data_str = f"Act: {event[6]}"
            if event[7]:  # forecast
                data_str += f" | Fct: {event[7]}"

            rows.append([
                event[0],  # date
                event[1],  # time
                event[2],  # event_name
                impact_display,
                event[4],  # country
                event[5],  # notes
                data_str
            ])

        if rows:
            worksheet.update(f'A2:G{len(rows)+1}', rows)

        print(f"✅ Created ECON Detail for {year}-{month:02d} ({len(rows)} events)")

    def export_month(self, year: int, month: int):
        """Export all tabs for a specific month"""
        sheet = self.get_or_create_sheet()
        if not sheet:
            print("❌ Cannot export - sheet not available")
            return

        print(f"📊 Exporting to Google Sheets: {year}-{month:02d}")

        self.create_monthly_overview(sheet, year, month)
        self.create_nba_detail(sheet, year, month)
        self.create_soccer_detail(sheet, year, month)
        self.create_econ_detail(sheet, year, month)

        print(f"✅ Export complete: {sheet.url}")

# CLI usage
if __name__ == '__main__':
    import sys
    from dotenv import load_dotenv
    load_dotenv()

    db_path = os.getenv('DB_PATH')
    creds_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
    sheet_id = os.getenv('GOOGLE_SHEET_ID')

    if not creds_path or not os.path.exists(creds_path):
        print("❌ Google Service Account JSON not found")
        print("   Please create credentials and update .env file")
        sys.exit(1)

    exporter = SheetsExporter(db_path, creds_path, sheet_id)

    if len(sys.argv) > 2:
        year = int(sys.argv[1])
        month = int(sys.argv[2])
    else:
        today = datetime.now()
        year = today.year
        month = today.month

    exporter.export_month(year, month)
