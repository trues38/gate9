"""
Storage - SQLite database for snapshots, patterns, and trades
"""
import sqlite3
import json
from datetime import datetime
from typing import List, Optional
from pathlib import Path


class Database:
    """SQLite database for trading engine"""

    def __init__(self, db_path: str = "data/btc_engine.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(str(self.db_path))

    def _init_db(self):
        """Initialize database tables"""
        conn = self._get_conn()
        cursor = conn.cursor()

        # Snapshots table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                price REAL NOT NULL,
                rsi REAL,
                bb_position REAL,
                fng INTEGER,
                funding_rate REAL,
                ls_ratio REAL,
                top_ls_ratio REAL,
                consecutive_down INTEGER,
                consecutive_up INTEGER,
                total_score INTEGER NOT NULL,
                verdict TEXT NOT NULL,
                signals_json TEXT
            )
        """)

        # Trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                type TEXT NOT NULL,  -- 'BUY' or 'SELL'
                price REAL NOT NULL,
                quantity REAL NOT NULL,
                score INTEGER,
                verdict TEXT,
                snapshot_id INTEGER,
                status TEXT DEFAULT 'OPEN',  -- 'OPEN', 'CLOSED', 'STOPPED'
                exit_price REAL,
                exit_timestamp TEXT,
                pnl REAL,
                pnl_pct REAL,
                notes TEXT,
                action_taken TEXT,  -- 'SIGNAL_BUY', 'SL_EXIT', 'TP_EXIT', 'TRAILING_EXIT', 'MANUAL_EXIT'
                oco_order_id TEXT,  -- OCO order ID for SL/TP tracking
                FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
            )
        """)

        # Migration: Add action_taken column to existing tables
        try:
            cursor.execute("ALTER TABLE trades ADD COLUMN action_taken TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists

        try:
            cursor.execute("ALTER TABLE trades ADD COLUMN oco_order_id TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Patterns table (for learned patterns)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                conditions_json TEXT NOT NULL,
                win_rate REAL,
                sample_count INTEGER,
                avg_return REAL,
                is_active INTEGER DEFAULT 1,
                created_at TEXT,
                updated_at TEXT
            )
        """)

        # Daily stats
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY,
                trades_count INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                total_pnl REAL DEFAULT 0,
                max_drawdown REAL DEFAULT 0
            )
        """)

        conn.commit()
        conn.close()

    def save_snapshot(self, snapshot) -> int:
        """Save market snapshot"""
        conn = self._get_conn()
        cursor = conn.cursor()

        signals_json = json.dumps([
            {"name": s.name, "value": s.value, "score": s.score, "desc": s.description}
            for s in snapshot.signals
        ])

        cursor.execute("""
            INSERT INTO snapshots (
                timestamp, price, rsi, bb_position, fng, funding_rate,
                ls_ratio, top_ls_ratio, consecutive_down, consecutive_up,
                total_score, verdict, signals_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            snapshot.timestamp.isoformat(),
            snapshot.price,
            snapshot.rsi,
            snapshot.bb_position,
            snapshot.fng,
            snapshot.funding_rate,
            snapshot.ls_ratio,
            snapshot.top_ls_ratio,
            snapshot.consecutive_down,
            snapshot.consecutive_up,
            snapshot.total_score,
            snapshot.verdict,
            signals_json
        ))

        snapshot_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return snapshot_id

    def save_trade(self, trade_type: str, price: float, quantity: float,
                   score: int, verdict: str, snapshot_id: int = None,
                   action_taken: str = None, oco_order_id: str = None) -> int:
        """Save a new trade

        action_taken: 'SIGNAL_BUY', 'SL_EXIT', 'TP_EXIT', 'TRAILING_EXIT', 'MANUAL_EXIT'
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO trades (timestamp, type, price, quantity, score, verdict, snapshot_id, action_taken, oco_order_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            trade_type,
            price,
            quantity,
            score,
            verdict,
            snapshot_id,
            action_taken,
            oco_order_id
        ))

        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return trade_id

    def close_trade(self, trade_id: int, exit_price: float, status: str = "CLOSED",
                    action_taken: str = None):
        """Close an open trade

        action_taken: 'SL_EXIT', 'TP_EXIT', 'TRAILING_EXIT', 'MANUAL_EXIT', 'OCO_SL', 'OCO_TP'
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        # Get original trade
        cursor.execute("SELECT price, quantity, type FROM trades WHERE id = ?", (trade_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None

        entry_price, quantity, trade_type = row

        # Calculate PnL
        if trade_type == "BUY":
            pnl = (exit_price - entry_price) * quantity
            pnl_pct = (exit_price - entry_price) / entry_price * 100
        else:  # SELL/SHORT
            pnl = (entry_price - exit_price) * quantity
            pnl_pct = (entry_price - exit_price) / entry_price * 100

        # Update with action_taken
        if action_taken:
            cursor.execute("""
                UPDATE trades SET
                    exit_price = ?,
                    exit_timestamp = ?,
                    status = ?,
                    pnl = ?,
                    pnl_pct = ?,
                    action_taken = COALESCE(action_taken || ' -> ', '') || ?
                WHERE id = ?
            """, (
                exit_price,
                datetime.now().isoformat(),
                status,
                pnl,
                pnl_pct,
                action_taken,
                trade_id
            ))
        else:
            cursor.execute("""
                UPDATE trades SET
                    exit_price = ?,
                    exit_timestamp = ?,
                    status = ?,
                    pnl = ?,
                    pnl_pct = ?
                WHERE id = ?
            """, (
                exit_price,
                datetime.now().isoformat(),
                status,
                pnl,
                pnl_pct,
                trade_id
            ))

        conn.commit()
        conn.close()
        return {"pnl": pnl, "pnl_pct": pnl_pct}

    def get_open_trades(self) -> List[dict]:
        """Get all open trades"""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, timestamp, type, price, quantity, score, verdict
            FROM trades WHERE status = 'OPEN'
            ORDER BY timestamp DESC
        """)

        trades = []
        for row in cursor.fetchall():
            trades.append({
                "id": row[0],
                "timestamp": row[1],
                "type": row[2],
                "price": row[3],
                "quantity": row[4],
                "score": row[5],
                "verdict": row[6]
            })

        conn.close()
        return trades

    def get_trade_stats(self, days: int = 30) -> dict:
        """Get trading statistics"""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END) as losses,
                SUM(pnl) as total_pnl,
                AVG(pnl_pct) as avg_pnl_pct
            FROM trades
            WHERE status != 'OPEN'
            AND datetime(timestamp) > datetime('now', ?)
        """, (f"-{days} days",))

        row = cursor.fetchone()
        conn.close()

        if row[0] == 0:
            return {"total": 0, "wins": 0, "losses": 0, "win_rate": 0, "total_pnl": 0, "avg_pnl_pct": 0}

        return {
            "total": row[0],
            "wins": row[1] or 0,
            "losses": row[2] or 0,
            "win_rate": (row[1] or 0) / row[0] * 100 if row[0] > 0 else 0,
            "total_pnl": row[3] or 0,
            "avg_pnl_pct": row[4] or 0
        }

    def get_recent_snapshots(self, limit: int = 100) -> List[dict]:
        """Get recent snapshots"""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT timestamp, price, total_score, verdict
            FROM snapshots
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        snapshots = []
        for row in cursor.fetchall():
            snapshots.append({
                "timestamp": row[0],
                "price": row[1],
                "score": row[2],
                "verdict": row[3]
            })

        conn.close()
        return snapshots
