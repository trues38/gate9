"""
Supabase to SQLite FULL Migration Script

Migrates ALL economic data from Supabase to local SQLite
"""

import sqlite3
import requests
import json
import os
from datetime import datetime
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ywkqvhtwjxclvjcdcyrv.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_secret_Zq7YcYxnbiO_naMBpXLHyw_WG8olhUm")
DB_PATH = os.getenv("ECON_DB_PATH", "data/economy_full.db")


class SupabaseToSQLiteFull:
    def __init__(self):
        self.supabase_url = SUPABASE_URL
        self.supabase_key = SUPABASE_KEY
        self.db_path = Path(DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}"
        }
        self.conn = None

    def connect(self):
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        logger.info(f"Connected to SQLite: {self.db_path}")

    def close(self):
        if self.conn:
            self.conn.close()

    def get_all_tables(self) -> list:
        """Get all tables from Supabase"""
        response = requests.get(f"{self.supabase_url}/rest/v1/", headers=self.headers)
        schema = response.json()
        return list(schema.get("definitions", {}).keys())

    def get_table_schema(self, table_name: str) -> dict:
        """Get table schema from OpenAPI"""
        response = requests.get(f"{self.supabase_url}/rest/v1/", headers=self.headers)
        schema = response.json()
        return schema.get("definitions", {}).get(table_name, {})

    def create_table_from_schema(self, table_name: str):
        """Dynamically create SQLite table from Supabase schema"""
        schema = self.get_table_schema(table_name)
        props = schema.get("properties", {})

        if not props:
            logger.warning(f"No schema found for {table_name}")
            return False

        # Map Supabase types to SQLite
        type_map = {
            "integer": "INTEGER",
            "number": "REAL",
            "string": "TEXT",
            "boolean": "INTEGER",
            "array": "TEXT",
            "object": "TEXT",
            "jsonb": "TEXT"
        }

        columns = []
        for col_name, col_spec in props.items():
            col_type = col_spec.get("type", col_spec.get("format", "text"))
            sqlite_type = type_map.get(col_type, "TEXT")
            columns.append(f'"{col_name}" {sqlite_type}')

        # Create table
        sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({", ".join(columns)})'

        cursor = self.conn.cursor()
        cursor.execute(sql)
        self.conn.commit()

        return True

    def get_table_count(self, table_name: str) -> int:
        """Get row count from Supabase table"""
        headers = {**self.headers, "Range-Unit": "items", "Range": "0-0", "Prefer": "count=exact"}
        response = requests.head(
            f"{self.supabase_url}/rest/v1/{table_name}?select=*",
            headers=headers
        )
        content_range = response.headers.get('content-range', '0/0')
        count = content_range.split('/')[-1]
        return int(count) if count.isdigit() else 0

    def fetch_batch(self, table_name: str, offset: int, limit: int = 1000) -> list:
        """Fetch a batch of rows from Supabase"""
        response = requests.get(
            f"{self.supabase_url}/rest/v1/{table_name}?select=*&offset={offset}&limit={limit}",
            headers=self.headers
        )
        if response.status_code == 200:
            return response.json()
        return []

    def migrate_table(self, table_name: str, batch_size: int = 1000):
        """Migrate a single table"""
        total_rows = self.get_table_count(table_name)
        logger.info(f"Migrating {table_name}: {total_rows:,} rows")

        if total_rows == 0:
            logger.info(f"  No data in {table_name}")
            return 0

        # Create table dynamically
        if not self.create_table_from_schema(table_name):
            return 0

        # Clear existing data
        cursor = self.conn.cursor()
        cursor.execute(f'DELETE FROM "{table_name}"')
        self.conn.commit()

        migrated = 0
        offset = 0

        while offset < total_rows:
            batch = self.fetch_batch(table_name, offset, batch_size)
            if not batch:
                break

            for row in batch:
                # Convert complex types to JSON strings
                processed_row = {}
                for key, value in row.items():
                    if isinstance(value, (dict, list)):
                        processed_row[key] = json.dumps(value)
                    else:
                        processed_row[key] = value

                columns = [f'"{c}"' for c in processed_row.keys()]
                placeholders = ",".join(["?" for _ in columns])
                values = list(processed_row.values())

                try:
                    cursor.execute(
                        f'INSERT OR REPLACE INTO "{table_name}" ({",".join(columns)}) VALUES ({placeholders})',
                        values
                    )
                except sqlite3.Error as e:
                    # Skip problematic rows
                    continue

            self.conn.commit()
            migrated += len(batch)
            offset += batch_size

            # Progress every 10%
            if total_rows > 1000 and migrated % (total_rows // 10 or 1) < batch_size:
                progress = (migrated / total_rows) * 100
                logger.info(f"  {table_name}: {migrated:,}/{total_rows:,} ({progress:.0f}%)")

        logger.info(f"  Completed {table_name}: {migrated:,} rows")
        return migrated

    def migrate_all(self, skip_large: bool = False, large_threshold: int = 100000):
        """Migrate all tables"""
        all_tables = self.get_all_tables()
        logger.info(f"Found {len(all_tables)} tables")

        # Get counts and sort by size
        table_counts = []
        for table in all_tables:
            count = self.get_table_count(table)
            table_counts.append((table, count))

        table_counts.sort(key=lambda x: x[1])

        total_migrated = 0
        for table, count in table_counts:
            if skip_large and count > large_threshold:
                logger.info(f"Skipping {table} ({count:,} rows) - exceeds threshold")
                continue

            try:
                migrated = self.migrate_table(table)
                total_migrated += migrated
            except Exception as e:
                logger.error(f"Failed {table}: {e}")

        return total_migrated

    def get_stats(self) -> dict:
        """Get database statistics"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]

        stats = {"tables": {}}
        for table in tables:
            cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
            count = cursor.fetchone()[0]
            if count > 0:
                stats["tables"][table] = count

        stats["total_rows"] = sum(stats["tables"].values())
        stats["db_size_mb"] = self.db_path.stat().st_size / (1024 * 1024)
        return stats


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-large", action="store_true", help="Skip tables > 100K rows")
    parser.add_argument("--tables", nargs="+", help="Specific tables to migrate")
    args = parser.parse_args()

    migrator = SupabaseToSQLiteFull()

    try:
        migrator.connect()

        if args.tables:
            for table in args.tables:
                migrator.migrate_table(table)
        else:
            migrator.migrate_all(skip_large=args.skip_large)

        # Print stats
        stats = migrator.get_stats()
        logger.info("\n=== Migration Stats ===")
        for table, count in sorted(stats["tables"].items(), key=lambda x: -x[1]):
            logger.info(f"  {table}: {count:,}")
        logger.info(f"  Total: {stats['total_rows']:,} rows")
        logger.info(f"  Size: {stats['db_size_mb']:.1f} MB")

    finally:
        migrator.close()


if __name__ == "__main__":
    main()
