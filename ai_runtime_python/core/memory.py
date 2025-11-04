"""Persistent memory layer for the AI daemon."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite


class ExperienceDB:
    """Asynchronous interface around a SQLite datastore."""

    def __init__(self, db_path: str):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[aiosqlite.Connection] = None
        self.init_db()

    def init_db(self) -> None:
        """Synchronously create tables if they do not exist."""
        with sqlite3.connect(self.path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recorded_at TEXT NOT NULL,
                    cpu REAL,
                    memory REAL,
                    disk REAL,
                    state_json TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    decided_at TEXT NOT NULL,
                    action TEXT,
                    confidence REAL,
                    decision_json TEXT NOT NULL,
                    state_json TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    async def _ensure_connection(self) -> aiosqlite.Connection:
        if self._conn is None:
            self._conn = await aiosqlite.connect(self.path)
            await self._conn.execute("PRAGMA journal_mode=WAL;")
            await self._conn.execute("PRAGMA foreign_keys=ON;")
        return self._conn

    async def log_metrics(self, state: Dict[str, Any]) -> None:
        conn = await self._ensure_connection()
        await conn.execute(
            """
            INSERT INTO metrics (recorded_at, cpu, memory, disk, state_json)
            VALUES (:recorded_at, :cpu, :memory, :disk, :state_json)
            """,
            {
                "recorded_at": state.get("timestamp"),
                "cpu": state.get("cpu_percent"),
                "memory": state.get("memory_percent"),
                "disk": state.get("disk_percent"),
                "state_json": json.dumps(state),
            },
        )
        await conn.commit()

    async def log_decision(self, decision: Dict[str, Any], state: Dict[str, Any]) -> None:
        conn = await self._ensure_connection()
        await conn.execute(
            """
            INSERT INTO decisions (decided_at, action, confidence, decision_json, state_json)
            VALUES (:decided_at, :action, :confidence, :decision_json, :state_json)
            """,
            {
                "decided_at": decision.get("timestamp") or state.get("timestamp"),
                "action": decision.get("action"),
                "confidence": decision.get("confidence"),
                "decision_json": json.dumps(decision),
                "state_json": json.dumps(state),
            },
        )
        await conn.commit()

    async def get_recent_context(self, limit: int = 25) -> List[Dict[str, Any]]:
        conn = await self._ensure_connection()
        cursor = await conn.execute(
            """
            SELECT decision_json
            FROM decisions
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
        return [json.loads(row[0]) for row in rows]

    async def analyze_patterns(self, window: int = 100) -> Dict[str, Any]:
        conn = await self._ensure_connection()
        cursor = await conn.execute(
            """
            SELECT cpu, memory, disk
            FROM metrics
            ORDER BY id DESC
            LIMIT ?
            """,
            (window,),
        )
        rows = await cursor.fetchall()
        if not rows:
            return {}
        cpu_avg = sum(row[0] or 0 for row in rows) / len(rows)
        mem_avg = sum(row[1] or 0 for row in rows) / len(rows)
        disk_avg = sum(row[2] or 0 for row in rows) / len(rows)
        return {
            "resource_trends": {
                "cpu_avg": cpu_avg,
                "memory_avg": mem_avg,
                "disk_avg": disk_avg,
            }
        }

    async def analyze_trends(self, key: str, window_hours: int = 24) -> Dict[str, Any]:
        """Analyze directionality for a particular metric key over time."""
        conn = await self._ensure_connection()
        cursor = await conn.execute(
            """
            SELECT recorded_at, state_json
            FROM metrics
            ORDER BY id DESC
            """,
        )
        rows = await cursor.fetchall()
        if not rows:
            return {}

        cutoff = datetime.utcnow() - timedelta(hours=window_hours)
        series: List[Dict[str, Any]] = []
        for recorded_at, state_json in rows:
            if not recorded_at:
                continue
            try:
                timestamp = datetime.fromisoformat(recorded_at)
            except ValueError:
                continue
            if timestamp < cutoff:
                break
            state = json.loads(state_json)
            value = self._extract_metric(state, key)
            if value is None:
                continue
            series.append({"timestamp": timestamp, "value": value})

        if len(series) < 2:
            return {}

        series.sort(key=lambda item: item["timestamp"])
        first = series[0]["value"]
        last = series[-1]["value"]
        if first in (0, None):
            trend_pct = None
        else:
            trend_pct = ((last - first) / first) * 100

        return {
            "metric": key,
            "current": last,
            "trend_percent": trend_pct,
            "direction": "up" if trend_pct and trend_pct > 0 else "down" if trend_pct and trend_pct < 0 else "flat",
            "samples": len(series),
        }

    async def record_event(self, kind: str, payload: Dict[str, Any], created_at: str) -> None:
        conn = await self._ensure_connection()
        await conn.execute(
            """
            INSERT INTO events (kind, payload_json, created_at)
            VALUES (?, ?, ?)
            """,
            (kind, json.dumps(payload), created_at),
        )
        await conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    @staticmethod
    def _extract_metric(state: Dict[str, Any], key: str) -> Optional[float]:
        """Extract dotted metric paths from stored state payloads."""
        if not state or not key:
            return None
        parts = key.split(".")
        value: Any = state
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        if isinstance(value, (int, float)):
            return float(value)
        return None
