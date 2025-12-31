"""
Supabase to SQLite Migration Script

Migrates economic data from Supabase to local SQLite for:
- Offline access on VPS
- Fast local queries
- Neo4j GraphRAG integration
"""

import sqlite3
import requests
import json
import os
import sys
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
DB_PATH = os.getenv("ECON_DB_PATH", "data/economy.db")

# Tables to migrate (ordered by importance)
TABLES_CONFIG = {
    "econ_indicators": {
        "schema": """
            CREATE TABLE IF NOT EXISTS econ_indicators (
                id INTEGER PRIMARY KEY,
                country TEXT,
                indicator TEXT,
                value REAL,
                value_prev REAL,
                value_consensus REAL,
                date TEXT,
                source TEXT,
                raw TEXT,
                created_at TEXT
            )
        """,
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_econ_country ON econ_indicators(country)",
            "CREATE INDEX IF NOT EXISTS idx_econ_indicator ON econ_indicators(indicator)",
            "CREATE INDEX IF NOT EXISTS idx_econ_date ON econ_indicators(date)"
        ]
    },
    "ingest_economics": {
        "schema": """
            CREATE TABLE IF NOT EXISTS ingest_economics (
                id TEXT PRIMARY KEY,
                date TEXT,
                country TEXT,
                indicator TEXT,
                ticker TEXT,
                value REAL,
                yoy_change REAL,
                mom_change REAL,
                created_at TEXT
            )
        """,
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_ingest_econ_date ON ingest_economics(date)",
            "CREATE INDEX IF NOT EXISTS idx_ingest_econ_country ON ingest_economics(country)"
        ]
    },
    "ingest_kosis_data": {
        "schema": """
            CREATE TABLE IF NOT EXISTS ingest_kosis_data (
                id INTEGER PRIMARY KEY,
                org_id TEXT,
                tbl_id TEXT,
                date TEXT,
                itm_id TEXT,
                obj_l1 TEXT,
                obj_l2 TEXT,
                value REAL,
                unit TEXT,
                created_at TEXT
            )
        """,
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_kosis_data_date ON ingest_kosis_data(date)",
            "CREATE INDEX IF NOT EXISTS idx_kosis_data_tbl ON ingest_kosis_data(tbl_id)"
        ]
    },
    "ingest_kosis_master": {
        "schema": """
            CREATE TABLE IF NOT EXISTS ingest_kosis_master (
                org_id TEXT,
                tbl_id TEXT,
                tbl_nm TEXT,
                meta_raw TEXT,
                last_crawled_at TEXT,
                PRIMARY KEY (org_id, tbl_id)
            )
        """,
        "indexes": []
    },
    "ingest_prices": {
        "schema": """
            CREATE TABLE IF NOT EXISTS ingest_prices (
                id TEXT PRIMARY KEY,
                date TEXT,
                ticker TEXT,
                close REAL,
                open REAL,
                high REAL,
                low REAL,
                volume INTEGER,
                country TEXT,
                created_at TEXT
            )
        """,
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_prices_date ON ingest_prices(date)",
            "CREATE INDEX IF NOT EXISTS idx_prices_ticker ON ingest_prices(ticker)"
        ]
    },
    "intelligence_regimes": {
        "schema": """
            CREATE TABLE IF NOT EXISTS intelligence_regimes (
                date TEXT,
                regime_name TEXT,
                signature TEXT,
                historical_vibe TEXT,
                structural_reasoning TEXT,
                risks TEXT,
                upside TEXT,
                created_at TEXT,
                PRIMARY KEY (date, regime_name)
            )
        """,
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_regimes_date ON intelligence_regimes(date)"
        ]
    },
    "ticker_ai_labels": {
        "schema": """
            CREATE TABLE IF NOT EXISTS ticker_ai_labels (
                id TEXT PRIMARY KEY,
                company TEXT,
                ticker TEXT,
                confidence REAL,
                candidate_tickers TEXT,
                reasoning TEXT,
                created_at TEXT
            )
        """,
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_ticker_labels ON ticker_ai_labels(ticker)"
        ]
    },
    "ticker_flow_map": {
        "schema": """
            CREATE TABLE IF NOT EXISTS ticker_flow_map (
                dt TEXT,
                ticker TEXT,
                category TEXT,
                freq INTEGER,
                ma30 REAL,
                delta REAL,
                vol REAL,
                spike_ratio REAL,
                PRIMARY KEY (dt, ticker)
            )
        """,
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_flow_dt ON ticker_flow_map(dt)",
            "CREATE INDEX IF NOT EXISTS idx_flow_ticker ON ticker_flow_map(ticker)"
        ]
    },
    "zscore_daily": {
        "schema": """
            CREATE TABLE IF NOT EXISTS zscore_daily (
                date TEXT PRIMARY KEY,
                count INTEGER,
                z_score REAL,
                z_year REAL,
                z_day_local REAL,
                impact_score REAL,
                created_at TEXT
            )
        """,
        "indexes": []
    },
    "rag_patterns": {
        "schema": """
            CREATE TABLE IF NOT EXISTS rag_patterns (
                id INTEGER PRIMARY KEY,
                pattern_id TEXT,
                name TEXT,
                description TEXT,
                conditions TEXT,
                historical_examples TEXT,
                created_at TEXT
            )
        """,
        "indexes": []
    },
    "rag_rules": {
        "schema": """
            CREATE TABLE IF NOT EXISTS rag_rules (
                id INTEGER PRIMARY KEY,
                rule_id TEXT,
                name TEXT,
                description TEXT,
                conditions TEXT,
                actions TEXT,
                created_at TEXT
            )
        """,
        "indexes": []
    }
}


class SupabaseToSQLite:
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
        """Connect to SQLite database"""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        logger.info(f"Connected to SQLite: {self.db_path}")

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def init_schema(self):
        """Initialize SQLite schema"""
        cursor = self.conn.cursor()

        for table_name, config in TABLES_CONFIG.items():
            logger.info(f"Creating table: {table_name}")
            cursor.execute(config["schema"])

            for idx_sql in config.get("indexes", []):
                cursor.execute(idx_sql)

        # Migration tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS _migration_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT,
                rows_migrated INTEGER,
                started_at TEXT,
                completed_at TEXT,
                status TEXT
            )
        """)

        self.conn.commit()
        logger.info("Schema initialized")

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
        else:
            logger.error(f"Error fetching {table_name}: {response.status_code}")
            return []

    def migrate_table(self, table_name: str, batch_size: int = 1000):
        """Migrate a single table from Supabase to SQLite"""
        if table_name not in TABLES_CONFIG:
            logger.warning(f"Table {table_name} not in config, skipping")
            return

        total_rows = self.get_table_count(table_name)
        logger.info(f"Migrating {table_name}: {total_rows:,} rows")

        if total_rows == 0:
            logger.info(f"  No data in {table_name}")
            return

        # Log migration start
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO _migration_log (table_name, rows_migrated, started_at, status) VALUES (?, 0, ?, 'running')",
            (table_name, datetime.now().isoformat())
        )
        log_id = cursor.lastrowid
        self.conn.commit()

        # Clear existing data
        cursor.execute(f"DELETE FROM {table_name}")
        self.conn.commit()

        migrated = 0
        offset = 0

        while offset < total_rows:
            batch = self.fetch_batch(table_name, offset, batch_size)
            if not batch:
                break

            # Insert batch
            for row in batch:
                # Convert JSON fields to strings
                processed_row = {}
                for key, value in row.items():
                    if isinstance(value, (dict, list)):
                        processed_row[key] = json.dumps(value)
                    else:
                        processed_row[key] = value

                columns = list(processed_row.keys())
                placeholders = ",".join(["?" for _ in columns])
                values = [processed_row[c] for c in columns]

                try:
                    cursor.execute(
                        f"INSERT OR REPLACE INTO {table_name} ({','.join(columns)}) VALUES ({placeholders})",
                        values
                    )
                except sqlite3.Error as e:
                    logger.error(f"Error inserting row: {e}")
                    continue

            self.conn.commit()
            migrated += len(batch)
            offset += batch_size

            # Progress log
            progress = (migrated / total_rows) * 100
            logger.info(f"  {table_name}: {migrated:,}/{total_rows:,} ({progress:.1f}%)")

        # Log migration complete
        cursor.execute(
            "UPDATE _migration_log SET rows_migrated=?, completed_at=?, status='completed' WHERE id=?",
            (migrated, datetime.now().isoformat(), log_id)
        )
        self.conn.commit()

        logger.info(f"  Completed {table_name}: {migrated:,} rows migrated")

    def migrate_all(self, tables: list = None):
        """Migrate all configured tables"""
        tables_to_migrate = tables or list(TABLES_CONFIG.keys())

        logger.info(f"Starting migration of {len(tables_to_migrate)} tables")

        for table_name in tables_to_migrate:
            try:
                self.migrate_table(table_name)
            except Exception as e:
                logger.error(f"Failed to migrate {table_name}: {e}")
                continue

        logger.info("Migration completed")

    def get_stats(self) -> dict:
        """Get migration statistics"""
        cursor = self.conn.cursor()

        stats = {"tables": {}}
        for table_name in TABLES_CONFIG.keys():
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            stats["tables"][table_name] = count

        stats["total_rows"] = sum(stats["tables"].values())
        stats["db_size_mb"] = self.db_path.stat().st_size / (1024 * 1024)

        return stats


def main():
    """Main entry point"""
    migrator = SupabaseToSQLite()

    try:
        migrator.connect()
        migrator.init_schema()

        # Migrate all tables
        migrator.migrate_all()

        # Print stats
        stats = migrator.get_stats()
        logger.info("\n=== Migration Stats ===")
        for table, count in stats["tables"].items():
            if count > 0:
                logger.info(f"  {table}: {count:,}")
        logger.info(f"  Total rows: {stats['total_rows']:,}")
        logger.info(f"  DB size: {stats['db_size_mb']:.2f} MB")

    finally:
        migrator.close()


if __name__ == "__main__":
    main()
