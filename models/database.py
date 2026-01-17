import aiosqlite
import json
from datetime import datetime
from typing import List, Optional
from config import settings

DATABASE_PATH = settings.DATABASE_PATH

async def init_database():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS opportunities (
                id TEXT PRIMARY KEY,
                detected_at TIMESTAMP NOT NULL,
                arbitrage_type TEXT NOT NULL,
                event_title TEXT,
                market_question TEXT,
                markets_involved TEXT,
                total_cost REAL NOT NULL,
                guaranteed_payout REAL NOT NULL,
                gross_profit REAL NOT NULL,
                gross_profit_percent REAL NOT NULL,
                estimated_fees REAL NOT NULL,
                net_profit REAL NOT NULL,
                net_profit_percent REAL NOT NULL,
                trade_legs TEXT,
                min_liquidity REAL,
                slug TEXT,
                is_active INTEGER DEFAULT 1,
                last_seen_at TIMESTAMP,
                times_detected INTEGER DEFAULT 1,
                expired_at TIMESTAMP
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TIMESTAMP NOT NULL,
                completed_at TIMESTAMP,
                markets_scanned INTEGER,
                opportunities_found INTEGER,
                duration_ms INTEGER,
                status TEXT DEFAULT 'running',
                error_message TEXT
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS market_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_id INTEGER,
                condition_id TEXT NOT NULL,
                question TEXT,
                price_sum REAL NOT NULL,
                token_prices TEXT,
                volume_24h REAL,
                liquidity REAL,
                snapshot_at TIMESTAMP NOT NULL
            )
        """)
        
        await db.commit()

async def save_opportunity(opp: dict) -> str:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        existing = await db.execute(
            "SELECT id, times_detected FROM opportunities WHERE id = ?",
            (opp["id"],)
        )
        row = await existing.fetchone()
        
        if row:
            times = row[1] + 1
            await db.execute("""
                UPDATE opportunities SET
                    last_seen_at = ?,
                    times_detected = ?,
                    is_active = 1,
                    net_profit = ?,
                    net_profit_percent = ?,
                    total_cost = ?
                WHERE id = ?
            """, (
                datetime.utcnow().isoformat(),
                times,
                opp["net_profit"],
                opp["net_profit_percent"],
                opp["total_cost"],
                opp["id"]
            ))
        else:
            await db.execute("""
                INSERT INTO opportunities (
                    id, detected_at, arbitrage_type, event_title, market_question,
                    markets_involved, total_cost, guaranteed_payout, gross_profit,
                    gross_profit_percent, estimated_fees, net_profit, net_profit_percent,
                    trade_legs, min_liquidity, slug, is_active, last_seen_at, times_detected
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, 1)
            """, (
                opp["id"],
                opp["detected_at"],
                opp["arbitrage_type"],
                opp.get("event_title"),
                opp["market_question"],
                json.dumps(opp["markets_involved"]),
                opp["total_cost"],
                opp["guaranteed_payout"],
                opp["gross_profit"],
                opp["gross_profit_percent"],
                opp["estimated_fees"],
                opp["net_profit"],
                opp["net_profit_percent"],
                json.dumps(opp["trade_legs"]),
                opp["min_liquidity"],
                opp.get("slug", ""),
                datetime.utcnow().isoformat()
            ))
        
        await db.commit()
        return opp["id"]

async def get_active_opportunities(limit: int = 100, min_profit: float = 0, sort: str = "profit") -> List[dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        order_by = "net_profit_percent DESC"
        if sort == "liquidity":
            order_by = "min_liquidity DESC"
        elif sort == "recent":
            order_by = "detected_at DESC"
        
        cursor = await db.execute(f"""
            SELECT * FROM opportunities 
            WHERE is_active = 1 AND net_profit_percent >= ?
            ORDER BY {order_by}
            LIMIT ?
        """, (min_profit, limit))
        
        rows = await cursor.fetchall()
        results = []
        for row in rows:
            opp = dict(row)
            opp["markets_involved"] = json.loads(opp["markets_involved"]) if opp["markets_involved"] else []
            opp["trade_legs"] = json.loads(opp["trade_legs"]) if opp["trade_legs"] else []
            results.append(opp)
        return results

async def get_opportunity_by_id(opp_id: str) -> Optional[dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM opportunities WHERE id = ?",
            (opp_id,)
        )
        row = await cursor.fetchone()
        if row:
            opp = dict(row)
            opp["markets_involved"] = json.loads(opp["markets_involved"]) if opp["markets_involved"] else []
            opp["trade_legs"] = json.loads(opp["trade_legs"]) if opp["trade_legs"] else []
            return opp
        return None

async def mark_opportunity_inactive(opp_id: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE opportunities SET is_active = 0, expired_at = ?
            WHERE id = ?
        """, (datetime.utcnow().isoformat(), opp_id))
        await db.commit()

async def mark_all_inactive():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE opportunities SET is_active = 0, expired_at = ?
            WHERE is_active = 1
        """, (datetime.utcnow().isoformat(),))
        await db.commit()

async def log_scan_start() -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO scans (started_at, status) VALUES (?, 'running')
        """, (datetime.utcnow().isoformat(),))
        await db.commit()
        return cursor.lastrowid

async def log_scan_complete(scan_id: int, markets_scanned: int, opportunities_found: int, duration_ms: int, error: str = None):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        status = "error" if error else "completed"
        await db.execute("""
            UPDATE scans SET
                completed_at = ?,
                markets_scanned = ?,
                opportunities_found = ?,
                duration_ms = ?,
                status = ?,
                error_message = ?
            WHERE id = ?
        """, (
            datetime.utcnow().isoformat(),
            markets_scanned,
            opportunities_found,
            duration_ms,
            status,
            error,
            scan_id
        ))
        await db.commit()

async def get_scan_history(limit: int = 50) -> List[dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM scans ORDER BY started_at DESC LIMIT ?
        """, (limit,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_summary_stats() -> dict:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        active = await db.execute("SELECT COUNT(*) as count FROM opportunities WHERE is_active = 1")
        active_row = await active.fetchone()
        
        profit = await db.execute("SELECT SUM(net_profit) as total FROM opportunities WHERE is_active = 1")
        profit_row = await profit.fetchone()
        
        best = await db.execute("SELECT MAX(net_profit_percent) as best FROM opportunities WHERE is_active = 1")
        best_row = await best.fetchone()
        
        scans = await db.execute("SELECT markets_scanned FROM scans ORDER BY id DESC LIMIT 1")
        scan_row = await scans.fetchone()
        
        return {
            "active_opportunities": active_row["count"] if active_row else 0,
            "total_profit_potential": profit_row["total"] if profit_row and profit_row["total"] else 0,
            "best_opportunity_percent": best_row["best"] if best_row and best_row["best"] else 0,
            "markets_scanned": scan_row["markets_scanned"] if scan_row and scan_row["markets_scanned"] else 0
        }
