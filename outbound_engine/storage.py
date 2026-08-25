"""SQLite-backed state: tracked targets, seen signals (for dedup), and generated briefs."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

from outbound_engine.config import DB_PATH, ensure_dirs
from outbound_engine.models import DailyBrief, Signal, Target

SCHEMA = """
CREATE TABLE IF NOT EXISTS targets (
    name TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    keywords TEXT NOT NULL DEFAULT '[]',
    linkedin_handle TEXT,
    x_handle TEXT,
    notes TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS signals (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    target TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    url TEXT,
    published_at TEXT,
    fetched_at TEXT NOT NULL,
    surfaced INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_signals_target ON signals(target);

CREATE TABLE IF NOT EXISTS briefs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    payload TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS repos (
    path TEXT PRIMARY KEY
);
"""


class Storage:
    def __init__(self, db_path: Path | str = DB_PATH):
        ensure_dirs()
        self.db_path = Path(db_path)
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # --- targets -----------------------------------------------------
    def upsert_target(self, target: Target) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO targets (name, type, keywords, linkedin_handle, x_handle, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    type=excluded.type,
                    keywords=excluded.keywords,
                    linkedin_handle=excluded.linkedin_handle,
                    x_handle=excluded.x_handle,
                    notes=excluded.notes
                """,
                (
                    target.name,
                    target.type,
                    json.dumps(target.keywords),
                    target.linkedin_handle,
                    target.x_handle,
                    target.notes,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def list_targets(self) -> list[Target]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM targets ORDER BY name").fetchall()
        return [
            Target(
                name=r["name"],
                type=r["type"],
                keywords=json.loads(r["keywords"]),
                linkedin_handle=r["linkedin_handle"],
                x_handle=r["x_handle"],
                notes=r["notes"],
            )
            for r in rows
        ]

    def remove_target(self, name: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM targets WHERE name = ?", (name,))
            return cur.rowcount > 0

    # --- signals -------------------------------------------------------
    def save_signals(self, signals: list[Signal]) -> list[Signal]:
        """Insert new signals, skipping ones already seen. Returns the ones that were new."""
        new_signals = []
        with self._connect() as conn:
            for s in signals:
                cur = conn.execute(
                    "SELECT 1 FROM signals WHERE id = ?", (s.id,)
                ).fetchone()
                if cur:
                    continue
                conn.execute(
                    """
                    INSERT INTO signals (id, source, target, title, body, url, published_at, fetched_at, surfaced)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                    """,
                    (
                        s.id,
                        s.source,
                        s.target,
                        s.title,
                        s.body,
                        s.url,
                        s.published_at,
                        s.fetched_at,
                    ),
                )
                new_signals.append(s)
        return new_signals

    def unsurfaced_signals(self, target: Optional[str] = None) -> list[Signal]:
        query = "SELECT * FROM signals WHERE surfaced = 0"
        params: tuple = ()
        if target:
            query += " AND target = ?"
            params = (target,)
        query += " ORDER BY fetched_at DESC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            Signal(
                id=r["id"],
                source=r["source"],
                target=r["target"],
                title=r["title"],
                body=r["body"],
                url=r["url"],
                published_at=r["published_at"],
                fetched_at=r["fetched_at"],
            )
            for r in rows
        ]

    def mark_surfaced(self, signal_ids: list[str]) -> None:
        if not signal_ids:
            return
        with self._connect() as conn:
            conn.executemany(
                "UPDATE signals SET surfaced = 1 WHERE id = ?",
                [(sid,) for sid in signal_ids],
            )

    # --- briefs ----------------------------------------------------------
    def save_brief(self, brief: DailyBrief) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO briefs (created_at, payload) VALUES (?, ?)",
                (datetime.now(timezone.utc).isoformat(), brief.model_dump_json()),
            )
            return cur.lastrowid

    def latest_brief(self) -> Optional[DailyBrief]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM briefs ORDER BY id DESC LIMIT 1"
            ).fetchone()
        if not row:
            return None
        return DailyBrief.model_validate_json(row["payload"])

    # --- watched repos (workspace context) --------------------------------
    def add_repo(self, path: str) -> None:
        with self._connect() as conn:
            conn.execute("INSERT OR IGNORE INTO repos (path) VALUES (?)", (path,))

    def list_repos(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT path FROM repos").fetchall()
        return [r["path"] for r in rows]
