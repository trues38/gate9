#!/usr/bin/env python3
"""
Markdown File Exporter
Creates MD files for pipeline consumption
"""

import os
import sqlite3
from datetime import datetime
from typing import List, Dict
from pathlib import Path

class MDExporter:
    def __init__(self, db_path: str, output_dir: str):
        self.db_path = db_path
        self.output_dir = output_dir

    def export_daily_schedule(self, date: str) -> str:
        """
        Export daily schedule as MD file
        Returns: path to created file
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all events for the day
        cursor.execute("SELECT * FROM nba_games WHERE date = ? ORDER BY time", (date,))
        nba_games = cursor.fetchall()

        cursor.execute("SELECT * FROM soccer_games WHERE date = ? ORDER BY time", (date,))
        soccer_games = cursor.fetchall()

        cursor.execute("SELECT * FROM econ_events WHERE date = ? ORDER BY time", (date,))
        econ_events = cursor.fetchall()

        conn.close()

        # Generate MD content
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        day_name = ['월', '화', '수', '목', '금', '토', '일'][date_obj.weekday()]

        md = f"# Daily Schedule — {date} ({day_name})\n\n"
        md += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        # ECON Events
        md += "## 📊 ECON Events\n\n"
        if econ_events:
            for event in econ_events:
                impact_emoji = {'HIGH': '🔴', 'MID': '🟡', 'LOW': '⚪'}.get(event[4], '')
                md += f"- **{event[2]}** {impact_emoji}\n"
                md += f"  - Time: {event[3]} KST\n"
                md += f"  - Event: {event[4]}\n"
                md += f"  - Impact: {event[5]}\n"
                if event[9]:
                    md += f"  - Notes: {event[9]}\n"
                md += "\n"
        else:
            md += "*No ECON events*\n\n"

        # NBA Games
        md += "## 🏀 NBA Games\n\n"
        if nba_games:
            for game in nba_games:
                importance_emoji = {'HIGH': '🔥', 'MID': '⚡', 'LOW': '⚪'}.get(game[5], '')
                md += f"- **{game[4]} @ {game[3]}** {importance_emoji}\n"
                md += f"  - Time: {game[2]} KST\n"
                md += f"  - Importance: {game[5]}\n"
                if game[8]:
                    md += f"  - Notes: {game[8]}\n"
                md += "\n"
        else:
            md += "*No NBA games*\n\n"

        # Soccer Games
        md += "## ⚽ Soccer Matches\n\n"
        if soccer_games:
            for game in soccer_games:
                importance_emoji = {'HIGH': '🔥', 'MID': '⚡', 'LOW': '⚪'}.get(game[6], '')
                md += f"- **[{game[3]}] {game[4]} vs {game[5]}** {importance_emoji}\n"
                md += f"  - Time: {game[2]} KST\n"
                md += f"  - Importance: {game[6]}\n"
                if game[8]:
                    md += f"  - Notes: {game[8]}\n"
                md += "\n"
        else:
            md += "*No soccer matches*\n\n"

        # Save file
        output_path = Path(self.output_dir) / 'daily' / f'schedule_{date}.md'
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md)

        print(f"✅ Created MD file: {output_path}")
        return str(output_path)

    def export_weekly_schedule(self, year: int, week: int) -> str:
        """Export weekly schedule"""
        # Get week date range
        from datetime import timedelta

        # First day of year
        jan1 = datetime(year, 1, 1)
        # Add weeks
        week_start = jan1 + timedelta(weeks=week-1)
        # Adjust to Monday
        week_start = week_start - timedelta(days=week_start.weekday())

        md = f"# Weekly Schedule — {year} Week {week}\n\n"
        md += f"Week: {week_start.strftime('%Y-%m-%d')} to {(week_start + timedelta(days=6)).strftime('%Y-%m-%d')}\n\n"

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for day_offset in range(7):
            day = week_start + timedelta(days=day_offset)
            date_str = day.strftime('%Y-%m-%d')
            day_name = ['월', '화', '수', '목', '금', '토', '일'][day.weekday()]

            md += f"## {date_str} ({day_name})\n\n"

            # Count events
            cursor.execute("SELECT COUNT(*) FROM econ_events WHERE date = ?", (date_str,))
            econ_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM nba_games WHERE date = ?", (date_str,))
            nba_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM soccer_games WHERE date = ?", (date_str,))
            soccer_count = cursor.fetchone()[0]

            md += f"- 📊 ECON: {econ_count} events\n"
            md += f"- 🏀 NBA: {nba_count} games\n"
            md += f"- ⚽ Soccer: {soccer_count} matches\n\n"

        conn.close()

        # Save file
        output_path = Path(self.output_dir) / 'weekly' / f'schedule_{year}_W{week:02d}.md'
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md)

        print(f"✅ Created weekly MD file: {output_path}")
        return str(output_path)

    def export_monthly_schedule(self, year: int, month: int) -> str:
        """Export monthly schedule"""
        from calendar import monthrange

        md = f"# Monthly Schedule — {year}-{month:02d}\n\n"

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        days_in_month = monthrange(year, month)[1]

        md += "| Date | ECON | NBA | Soccer |\n"
        md += "|------|------|-----|--------|\n"

        for day in range(1, days_in_month + 1):
            date_str = f"{year}-{month:02d}-{day:02d}"

            cursor.execute("SELECT COUNT(*) FROM econ_events WHERE date = ?", (date_str,))
            econ_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM nba_games WHERE date = ?", (date_str,))
            nba_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM soccer_games WHERE date = ?", (date_str,))
            soccer_count = cursor.fetchone()[0]

            md += f"| {month}/{day} | {econ_count} | {nba_count} | {soccer_count} |\n"

        conn.close()

        # Save file
        output_path = Path(self.output_dir) / 'monthly' / f'schedule_{year}_{month:02d}.md'
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md)

        print(f"✅ Created monthly MD file: {output_path}")
        return str(output_path)

# CLI usage
if __name__ == '__main__':
    import sys
    from dotenv import load_dotenv
    load_dotenv()

    db_path = os.getenv('DB_PATH')
    output_dir = os.getenv('OUTPUT_DIR', '/Users/js/g9/scheduler/outputs')

    exporter = MDExporter(db_path, output_dir)

    if len(sys.argv) > 1:
        mode = sys.argv[1]

        if mode == 'daily' and len(sys.argv) > 2:
            date = sys.argv[2]  # YYYY-MM-DD
            exporter.export_daily_schedule(date)

        elif mode == 'weekly' and len(sys.argv) > 3:
            year = int(sys.argv[2])
            week = int(sys.argv[3])
            exporter.export_weekly_schedule(year, week)

        elif mode == 'monthly' and len(sys.argv) > 3:
            year = int(sys.argv[2])
            month = int(sys.argv[3])
            exporter.export_monthly_schedule(year, month)

    else:
        # Default: today
        today = datetime.now().strftime('%Y-%m-%d')
        exporter.export_daily_schedule(today)
