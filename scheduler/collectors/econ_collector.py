#!/usr/bin/env python3
"""
ECON Events Collector
Combines FRED API data with hardcoded major economic events
"""

import os
import sqlite3
import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict
from pathlib import Path

class EconCollector:
    def __init__(self, db_path: str, fred_api_key: str = None):
        self.db_path = db_path
        self.fred_api_key = fred_api_key
        self.fred_base_url = "https://api.stlouisfed.org/fred"

        # Load hardcoded events calendar
        events_file = Path(__file__).parent / 'econ_events.json'
        with open(events_file, 'r') as f:
            self.events_data = json.load(f)

    def load_calendar_events(self, year: int = None, month: int = None) -> List[Dict]:
        """Load hardcoded calendar events"""
        # Load all calendar events (2025 + 2026)
        calendar = self.events_data.get('2025_calendar', [])
        event_definitions = {
            e['name']: e for e in self.events_data.get('recurring_events', [])
        }

        events = []
        for entry in calendar:
            date_str = entry['date']
            event_name = entry['event']
            time_str = entry['time']

            # Filter by year/month if specified
            if year and month:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                if date_obj.year != year or date_obj.month != month:
                    continue

            # Get event details
            event_def = event_definitions.get(event_name, {})

            events.append({
                'id': f"econ_{date_str}_{event_name}",
                'date': date_str,
                'time': time_str,
                'event_name': event_def.get('full_name', event_name),
                'impact': event_def.get('impact', 'MID'),
                'country': event_def.get('country', 'US'),
                'actual': None,
                'forecast': None,
                'previous': None,
                'notes': event_def.get('description', '')
            })

        return events

    def fetch_fred_releases(self, date_from: str = None, date_to: str = None) -> List[Dict]:
        """
        Fetch economic data releases from FRED API
        (Optional - can enhance with real-time data)
        """
        if not self.fred_api_key:
            return []

        # Implementation for FRED API
        # Can fetch actual CPI, GDP numbers when released
        return []

    def get_month_events(self, year: int, month: int) -> List[Dict]:
        """Get all events for a specific month"""
        print(f"📊 Loading ECON events for {year}-{month:02d}")
        events = self.load_calendar_events(year, month)
        print(f"  Found {len(events)} events")
        return events

    def get_upcoming_events(self, days: int = 7) -> List[Dict]:
        """Get events for next N days"""
        today = datetime.now()
        all_events = self.load_calendar_events()

        upcoming = []
        for event in all_events:
            event_date = datetime.strptime(event['date'], '%Y-%m-%d')
            if 0 <= (event_date - today).days <= days:
                upcoming.append(event)

        return upcoming

    def save_to_db(self, events: List[Dict]):
        """Save events to SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for event in events:
            cursor.execute("""
                INSERT OR REPLACE INTO econ_events
                (id, date, time, event_name, impact, country, actual, forecast, previous, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event['id'],
                event['date'],
                event['time'],
                event['event_name'],
                event['impact'],
                event['country'],
                event.get('actual'),
                event.get('forecast'),
                event.get('previous'),
                event.get('notes', '')
            ))

        conn.commit()
        conn.close()

        print(f"✅ Saved {len(events)} ECON events to database")

    def collect_and_save(self, year: int = None, month: int = None):
        """Main method: collect and save events"""
        if year and month:
            events = self.get_month_events(year, month)
        else:
            # Get current month by default
            today = datetime.now()
            events = self.get_month_events(today.year, today.month)

        if events:
            self.save_to_db(events)

        return events

# CLI usage
if __name__ == '__main__':
    import sys
    from dotenv import load_dotenv
    load_dotenv()

    db_path = os.getenv('DB_PATH', '/Users/js/g9/scheduler/data/schedules.db')
    fred_api_key = os.getenv('FRED_API_KEY')

    collector = EconCollector(db_path, fred_api_key)

    if len(sys.argv) > 2:
        # Specific month: YYYY MM
        year = int(sys.argv[1])
        month = int(sys.argv[2])
        events = collector.collect_and_save(year, month)
    else:
        # Current month
        events = collector.collect_and_save()

    print(f"\n📊 Summary: {len(events)} events collected")
    for event in events:
        print(f"  {event['date']} {event['time']} - {event['event_name']} [{event['impact']}]")
