"""
hash_chain.py
-------------
Tamper-evident audit log: every entry stores a hash of the PREVIOUS
entry's hash plus its own content. If anyone edits an old record
directly in the database, its hash no longer matches what was computed
at write time, and every subsequent entry's hash becomes invalid too --
tampering with entry N breaks the chain for everything after N, making
it detectable rather than silently accepted.

This achieves the same tamper-evidence guarantee a blockchain would
provide for this use case, without the operational overhead of running
a separate blockchain node -- see the capstone report for the explicit
reasoning behind this choice.
"""

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "nexus.db"
GENESIS_HASH = "0" * 64  # the fixed starting point of the chain


@dataclass
class AuditEntry:
    id: int
    timestamp: str
    event_type: str
    actor: str
    details: str
    prev_hash: str
    entry_hash: str


class AuditLog:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._ensure_table()

    def _ensure_table(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                actor TEXT NOT NULL,
                details TEXT NOT NULL,
                prev_hash TEXT NOT NULL,
                entry_hash TEXT NOT NULL
            )"""
        )
        conn.commit()
        conn.close()

    def _compute_hash(self, prev_hash: str, timestamp: str, event_type: str, actor: str, details: str) -> str:
        payload = json.dumps(
            {"prev_hash": prev_hash, "timestamp": timestamp, "event_type": event_type,
             "actor": actor, "details": details},
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    def _get_last_hash(self, conn: sqlite3.Connection) -> str:
        row = conn.execute("SELECT entry_hash FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
        return row[0] if row else GENESIS_HASH

    def append(self, event_type: str, actor: str, details: str) -> AuditEntry:
        conn = sqlite3.connect(self.db_path)
        prev_hash = self._get_last_hash(conn)
        timestamp = datetime.now(timezone.utc).isoformat()
        entry_hash = self._compute_hash(prev_hash, timestamp, event_type, actor, details)

        cursor = conn.execute(
            """INSERT INTO audit_log (timestamp, event_type, actor, details, prev_hash, entry_hash)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (timestamp, event_type, actor, details, prev_hash, entry_hash),
        )
        conn.commit()
        entry_id = cursor.lastrowid
        conn.close()

        return AuditEntry(
            id=entry_id, timestamp=timestamp, event_type=event_type, actor=actor,
            details=details, prev_hash=prev_hash, entry_hash=entry_hash,
        )

    def get_all_entries(self) -> list[AuditEntry]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM audit_log ORDER BY id ASC").fetchall()
        conn.close()
        return [AuditEntry(**dict(r)) for r in rows]

    def verify_integrity(self) -> tuple[bool, str | None]:
        """
        Walks the entire chain and recomputes each hash from scratch.
        Returns (True, None) if the chain is intact, or (False, reason)
        pointing to the first entry where tampering is detected.
        """
        entries = self.get_all_entries()
        expected_prev = GENESIS_HASH

        for entry in entries:
            if entry.prev_hash != expected_prev:
                return False, f"Entry {entry.id}: prev_hash link broken (chain tampered before this point)"

            recomputed = self._compute_hash(
                entry.prev_hash, entry.timestamp, entry.event_type, entry.actor, entry.details
            )
            if recomputed != entry.entry_hash:
                return False, f"Entry {entry.id}: content does not match its recorded hash (record was edited)"

            expected_prev = entry.entry_hash

        return True, None
