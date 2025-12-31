#!/usr/bin/env python3
"""
Google Calendar Exporter
Creates calendar events for NBA/Soccer/ECON and review tasks
"""

import os
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

class CalendarExporter:
    def __init__(self, db_path: str, credentials_path: str, calendar_id: str = 'primary'):
        self.db_path = db_path
        self.calendar_id = calendar_id

        # Authenticate with Google
        try:
            creds = Credentials.from_service_account_file(
                credentials_path,
                scopes=['https://www.googleapis.com/auth/calendar']
            )
            self.service = build('calendar', 'v3', credentials=creds)
            print("✅ Google Calendar authentication successful")
        except Exception as e:
            print(f"❌ Google Calendar authentication failed: {e}")
            self.service = None

    def clear_events(self, date_from: str, date_to: str):
        """Clear existing G9 events in date range"""
        if not self.service:
            return

        try:
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=f"{date_from}T00:00:00Z",
                timeMax=f"{date_to}T23:59:59Z",
                q='[G9]',
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])

            for event in events:
                self.service.events().delete(
                    calendarId=self.calendar_id,
                    eventId=event['id']
                ).execute()

            print(f"🗑️  Cleared {len(events)} existing G9 events")

        except Exception as e:
            print(f"⚠️  Error clearing events: {e}")

    def create_nba_events(self, year: int, month: int):
        """Create NBA game events"""
        if not self.service:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT date, time, home_team, away_team, importance
            FROM nba_games
            WHERE date LIKE ?
            ORDER BY date, time
        """, (f"{year}-{month:02d}%",))

        games = cursor.fetchall()
        conn.close()

        created = 0
        for game in games:
            date_str, time_str, home, away, importance = game

            # Create datetime
            dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

            # Emoji for importance
            emoji = {'HIGH': '🔥', 'MID': '⚡', 'LOW': ''}.get(importance, '')

            summary = f"[NBA] {away} @ {home} {emoji}"
            description = f"Importance: {importance}"

            event = {
                'summary': summary,
                'description': description,
                'start': {
                    'dateTime': dt.isoformat(),
                    'timeZone': 'Asia/Seoul',
                },
                'end': {
                    'dateTime': (dt + timedelta(hours=3)).isoformat(),
                    'timeZone': 'Asia/Seoul',
                },
                'colorId': '11'  # Red for NBA
            }

            try:
                self.service.events().insert(calendarId=self.calendar_id, body=event).execute()
                created += 1
            except Exception as e:
                print(f"⚠️  Error creating NBA event: {e}")

        print(f"✅ Created {created} NBA events")

    def create_soccer_events(self, year: int, month: int):
        """Create Soccer match events"""
        if not self.service:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT date, time, league, home_team, away_team, importance
            FROM soccer_games
            WHERE date LIKE ?
            ORDER BY date, time
        """, (f"{year}-{month:02d}%",))

        games = cursor.fetchall()
        conn.close()

        created = 0
        for game in games:
            date_str, time_str, league, home, away, importance = game

            dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

            emoji = {'HIGH': '🔥', 'MID': '⚡', 'LOW': ''}.get(importance, '')

            summary = f"[{league}] {home} vs {away} {emoji}"
            description = f"Importance: {importance}"

            event = {
                'summary': summary,
                'description': description,
                'start': {
                    'dateTime': dt.isoformat(),
                    'timeZone': 'Asia/Seoul',
                },
                'end': {
                    'dateTime': (dt + timedelta(hours=2)).isoformat(),
                    'timeZone': 'Asia/Seoul',
                },
                'colorId': '10'  # Green for Soccer
            }

            try:
                self.service.events().insert(calendarId=self.calendar_id, body=event).execute()
                created += 1
            except Exception as e:
                print(f"⚠️  Error creating Soccer event: {e}")

        print(f"✅ Created {created} Soccer events")

    def create_econ_events(self, year: int, month: int):
        """Create ECON events"""
        if not self.service:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT date, time, event_name, impact
            FROM econ_events
            WHERE date LIKE ?
            ORDER BY date, time
        """, (f"{year}-{month:02d}%",))

        events = cursor.fetchall()
        conn.close()

        created = 0
        for ev in events:
            date_str, time_str, event_name, impact = ev

            dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

            emoji = '⚠️' if impact == 'HIGH' else ''

            summary = f"[ECON] {event_name} {emoji}"
            description = f"Impact: {impact}"

            event = {
                'summary': summary,
                'description': description,
                'start': {
                    'dateTime': dt.isoformat(),
                    'timeZone': 'Asia/Seoul',
                },
                'end': {
                    'dateTime': (dt + timedelta(minutes=30)).isoformat(),
                    'timeZone': 'Asia/Seoul',
                },
                'colorId': '1'  # Blue for ECON
            }

            try:
                self.service.events().insert(calendarId=self.calendar_id, body=event).execute()
                created += 1
            except Exception as e:
                print(f"⚠️  Error creating ECON event: {e}")

        print(f"✅ Created {created} ECON events")

    def create_review_tasks(self, year: int, month: int):
        """
        Create my review tasks based on schedule
        - ECON review: 30min before first ECON event
        - NBA review: 1 hour before first NBA game
        - Soccer review: 1 hour before first soccer match
        """
        if not self.service:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        from calendar import monthrange
        days_in_month = monthrange(year, month)[1]

        created = 0
        for day in range(1, days_in_month + 1):
            date_str = f"{year}-{month:02d}-{day:02d}"

            # Check for ECON events
            cursor.execute("""
                SELECT MIN(time) FROM econ_events WHERE date = ?
            """, (date_str,))
            result = cursor.fetchone()
            if result and result[0]:
                time_str = result[0]
                dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                review_time = dt - timedelta(minutes=30)

                event = {
                    'summary': '[G9] ECON 검토',
                    'description': 'Review ECON events and prepare reports',
                    'start': {
                        'dateTime': review_time.isoformat(),
                        'timeZone': 'Asia/Seoul',
                    },
                    'end': {
                        'dateTime': (review_time + timedelta(minutes=30)).isoformat(),
                        'timeZone': 'Asia/Seoul',
                    },
                    'colorId': '8'  # Gray for tasks
                }

                try:
                    self.service.events().insert(calendarId=self.calendar_id, body=event).execute()
                    created += 1
                except Exception as e:
                    pass

            # Check for NBA games
            cursor.execute("""
                SELECT MIN(time) FROM nba_games WHERE date = ?
            """, (date_str,))
            result = cursor.fetchone()
            if result and result[0]:
                time_str = result[0]
                dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                review_time = dt - timedelta(hours=1)

                event = {
                    'summary': '[G9] NBA 검토',
                    'description': 'Review NBA matchups and prepare reports',
                    'start': {
                        'dateTime': review_time.isoformat(),
                        'timeZone': 'Asia/Seoul',
                    },
                    'end': {
                        'dateTime': (review_time + timedelta(minutes=30)).isoformat(),
                        'timeZone': 'Asia/Seoul',
                    },
                    'colorId': '8'
                }

                try:
                    self.service.events().insert(calendarId=self.calendar_id, body=event).execute()
                    created += 1
                except Exception as e:
                    pass

            # Check for Soccer games
            cursor.execute("""
                SELECT MIN(time) FROM soccer_games WHERE date = ?
            """, (date_str,))
            result = cursor.fetchone()
            if result and result[0]:
                time_str = result[0]
                dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                review_time = dt - timedelta(hours=1)

                event = {
                    'summary': '[G9] SOCCER 검토',
                    'description': 'Review Soccer matches and prepare reports',
                    'start': {
                        'dateTime': review_time.isoformat(),
                        'timeZone': 'Asia/Seoul',
                    },
                    'end': {
                        'dateTime': (review_time + timedelta(minutes=30)).isoformat(),
                        'timeZone': 'Asia/Seoul',
                    },
                    'colorId': '8'
                }

                try:
                    self.service.events().insert(calendarId=self.calendar_id, body=event).execute()
                    created += 1
                except Exception as e:
                    pass

        conn.close()
        print(f"✅ Created {created} review task events")

    def export_month(self, year: int, month: int, clear_existing: bool = True):
        """Export all events for a month to Google Calendar"""
        if not self.service:
            print("❌ Cannot export - calendar service not available")
            return

        print(f"📅 Exporting to Google Calendar: {year}-{month:02d}")

        # Clear existing events if requested
        if clear_existing:
            from calendar import monthrange
            days_in_month = monthrange(year, month)[1]
            date_from = f"{year}-{month:02d}-01"
            date_to = f"{year}-{month:02d}-{days_in_month}"
            self.clear_events(date_from, date_to)

        # Create new events
        self.create_econ_events(year, month)
        self.create_nba_events(year, month)
        self.create_soccer_events(year, month)
        self.create_review_tasks(year, month)

        print(f"✅ Calendar export complete")

# CLI usage
if __name__ == '__main__':
    import sys
    from dotenv import load_dotenv
    load_dotenv()

    db_path = os.getenv('DB_PATH')
    creds_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
    calendar_id = os.getenv('GOOGLE_CALENDAR_ID', 'primary')

    if not creds_path or not os.path.exists(creds_path):
        print("❌ Google Service Account JSON not found")
        sys.exit(1)

    exporter = CalendarExporter(db_path, creds_path, calendar_id)

    if len(sys.argv) > 2:
        year = int(sys.argv[1])
        month = int(sys.argv[2])
    else:
        today = datetime.now()
        year = today.year
        month = today.month

    exporter.export_month(year, month)
