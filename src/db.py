"""SQLite persistence for PRD-shaped WatchMan alerts and auth."""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from watchman_config import DB_PATH


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    resolved = Path(os.getenv("WATCHMAN_DB_PATH")) if os.getenv("WATCHMAN_DB_PATH") else Path(db_path or DB_PATH)
    resolved.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(resolved), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: Path | None = None) -> None:
    conn = connect(db_path)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('viewer','admin','superadmin')),
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS alerts_v2 (
            alert_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            attack_type TEXT NOT NULL,
            source_ip TEXT,
            destination_ip TEXT,
            source_port INTEGER,
            destination_port INTEGER,
            confidence_score REAL NOT NULL,
            protocol TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            anchor_status TEXT NOT NULL DEFAULT 'pending',
            batch_id TEXT,
            merkle_root TEXT,
            merkle_proof TEXT,
            polygon_tx_hash TEXT,
            alert_hash TEXT NOT NULL,
            raw_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS anchor_batches (
            batch_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            merkle_root TEXT NOT NULL,
            alert_count INTEGER NOT NULL,
            status TEXT NOT NULL,
            polygon_tx_hash TEXT,
            error TEXT
        );

        CREATE TABLE IF NOT EXISTS runtime_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS blocked_ips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT UNIQUE NOT NULL,
            reason TEXT,
            blocked_at TEXT NOT NULL,
            blocked_by TEXT NOT NULL
        );
        """
    )
    _migrate_legacy_alerts(conn)
    conn.commit()
    conn.close()


def _migrate_legacy_alerts(conn: sqlite3.Connection) -> None:
    legacy_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='alerts'"
    ).fetchone()
    if not legacy_exists:
        return
    rows = conn.execute("SELECT * FROM alerts").fetchall()
    for row in rows:
        row_dict = dict(row)
        legacy_id = row_dict.get("id")
        alert_id = f"legacy-{legacy_id}" if legacy_id is not None else str(uuid.uuid4())
        exists = conn.execute(
            "SELECT 1 FROM alerts_v2 WHERE alert_id=?", (alert_id,)
        ).fetchone()
        if exists:
            continue
        attack_type = row_dict.get("alert_type") or row_dict.get("label") or "anomaly"
        confidence = row_dict.get("confidence") or row_dict.get("confidence_score") or 0
        if confidence and confidence > 1:
            confidence = float(confidence) / 100.0
        raw_json = json.dumps(row_dict, sort_keys=True, default=str)
        alert_hash = row_dict.get("alert_hash") or uuid.uuid5(uuid.NAMESPACE_URL, raw_json).hex
        conn.execute(
            """
            INSERT INTO alerts_v2 (
                alert_id, timestamp, attack_type, source_ip, destination_ip,
                source_port, destination_port, confidence_score, protocol,
                status, anchor_status, batch_id, merkle_root, merkle_proof,
                polygon_tx_hash, alert_hash, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                alert_id,
                row_dict.get("timestamp") or utc_now(),
                str(attack_type).lower(),
                row_dict.get("src_ip"),
                row_dict.get("dst_ip"),
                row_dict.get("src_port"),
                row_dict.get("dst_port"),
                float(confidence or 0),
                str(row_dict.get("protocol") or ""),
                row_dict.get("status") or "active",
                "confirmed" if row_dict.get("tx_hash") else "pending",
                None,
                None,
                None,
                row_dict.get("tx_hash"),
                alert_hash,
                raw_json,
            ),
        )


def upsert_user(username: str, password_hash: str, role: str) -> None:
    conn = connect()
    conn.execute(
        """
        INSERT INTO users (username, password_hash, role, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash, role=excluded.role
        """,
        (username, password_hash, role, utc_now()),
    )
    conn.commit()
    conn.close()


def get_user(username: str) -> dict[str, Any] | None:
    conn = connect()
    row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None


def insert_alert(alert: dict[str, Any]) -> dict[str, Any]:
    from merkle import canonical_alert_hash

    alert_id = alert.get("alert_id") or str(uuid.uuid4())
    record = {
        "alert_id": alert_id,
        "timestamp": alert.get("timestamp") or utc_now(),
        "attack_type": str(alert.get("attack_type") or alert.get("label") or "anomaly").lower(),
        "source_ip": alert.get("source_ip") or alert.get("src_ip"),
        "destination_ip": alert.get("destination_ip") or alert.get("dst_ip"),
        "source_port": int(alert.get("source_port") or alert.get("src_port") or 0),
        "destination_port": int(alert.get("destination_port") or alert.get("dst_port") or 0),
        "confidence_score": float(alert.get("confidence_score") or alert.get("rf_confidence") or 0),
        "protocol": str(alert.get("protocol") or ""),
        "status": alert.get("status") or "active",
    }
    raw = json.dumps(record, sort_keys=True, separators=(",", ":"))
    alert_hash = canonical_alert_hash(record)
    conn = connect()
    conn.execute(
        """
        INSERT INTO alerts_v2 (
            alert_id, timestamp, attack_type, source_ip, destination_ip,
            source_port, destination_port, confidence_score, protocol,
            status, anchor_status, alert_hash, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
        """,
        (
            record["alert_id"],
            record["timestamp"],
            record["attack_type"],
            record["source_ip"],
            record["destination_ip"],
            record["source_port"],
            record["destination_port"],
            record["confidence_score"],
            record["protocol"],
            record["status"],
            alert_hash,
            raw,
        ),
    )
    conn.commit()
    conn.close()
    return get_alert(alert_id) or record


def list_alerts(limit: int = 50, attack_type: str | None = None, hours: int | None = None) -> list[dict[str, Any]]:
    conn = connect()
    clauses: list[str] = []
    params: list[Any] = []
    if attack_type:
        clauses.append("attack_type = ?")
        params.append(attack_type.lower())
    if hours:
        clauses.append("timestamp >= datetime('now', ?)")
        params.append(f"-{int(hours)} hours")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = conn.execute(
        f"SELECT * FROM alerts_v2 {where} ORDER BY timestamp DESC LIMIT ?",
        (*params, int(limit)),
    ).fetchall()
    conn.close()
    return [_decode_alert(dict(row)) for row in rows]


def get_alert(alert_id: str) -> dict[str, Any] | None:
    conn = connect()
    row = conn.execute(
        "SELECT * FROM alerts_v2 WHERE alert_id=?", (str(alert_id),)
    ).fetchone()
    conn.close()
    return _decode_alert(dict(row)) if row else None


def get_pending_alerts() -> list[dict[str, Any]]:
    conn = connect()
    rows = conn.execute(
        "SELECT * FROM alerts_v2 WHERE anchor_status='pending' ORDER BY timestamp ASC"
    ).fetchall()
    conn.close()
    return [_decode_alert(dict(row)) for row in rows]


def mark_batch(batch_id: str, alerts: list[dict[str, Any]], merkle_root: str, status: str, tx_hash: str | None = None, error: str | None = None) -> None:
    conn = connect()
    conn.execute(
        """
        INSERT INTO anchor_batches (batch_id, created_at, merkle_root, alert_count, status, polygon_tx_hash, error)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (batch_id, utc_now(), merkle_root, len(alerts), status, tx_hash, error),
    )
    for alert in alerts:
        conn.execute(
            """
            UPDATE alerts_v2
            SET anchor_status=?, batch_id=?, merkle_root=?, merkle_proof=?, polygon_tx_hash=?
            WHERE alert_id=?
            """,
            (
                status,
                batch_id,
                merkle_root,
                json.dumps(alert.get("merkle_proof") or []),
                tx_hash,
                alert["alert_id"],
            ),
        )
    conn.commit()
    conn.close()


def stats() -> dict[str, Any]:
    conn = connect()
    total = conn.execute("SELECT COUNT(*) FROM alerts_v2").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM alerts_v2 WHERE anchor_status='pending'").fetchone()[0]
    confirmed = conn.execute("SELECT COUNT(*) FROM alerts_v2 WHERE anchor_status='confirmed'").fetchone()[0]
    by_type = conn.execute(
        "SELECT attack_type, COUNT(*) count FROM alerts_v2 GROUP BY attack_type"
    ).fetchall()
    avg_conf = conn.execute("SELECT AVG(confidence_score) FROM alerts_v2").fetchone()[0] or 0
    conn.close()
    return {
        "total_alerts": total,
        "pending_anchors": pending,
        "confirmed_anchors": confirmed,
        "average_confidence": round(float(avg_conf), 4),
        "by_attack_type": {row["attack_type"]: row["count"] for row in by_type},
    }


def set_state(key: str, value: Any) -> None:
    conn = connect()
    conn.execute(
        "INSERT OR REPLACE INTO runtime_state (key, value) VALUES (?, ?)",
        (key, json.dumps(value)),
    )
    conn.commit()
    conn.close()


def get_state(key: str, default: Any = None) -> Any:
    conn = connect()
    row = conn.execute("SELECT value FROM runtime_state WHERE key=?", (key,)).fetchone()
    conn.close()
    return json.loads(row["value"]) if row else default


def _decode_alert(row: dict[str, Any]) -> dict[str, Any]:
    proof = row.get("merkle_proof")
    row["merkle_proof"] = json.loads(proof) if proof else []
    return row
