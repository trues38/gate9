#!/usr/bin/env python3
"""Initialize SQLite database with schema"""

import sqlite3
import os
from pathlib import Path

def init_database(db_path: str):
    """Initialize database with schema"""
    # Create directory if not exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Read schema
    schema_path = Path(__file__).parent / 'schema.sql'
    with open(schema_path, 'r') as f:
        schema = f.read()

    # Create database and execute schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executescript(schema)
    conn.commit()
    conn.close()

    print(f"✅ Database initialized: {db_path}")

if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()

    db_path = os.getenv('DB_PATH', '/Users/js/g9/scheduler/data/schedules.db')
    init_database(db_path)
