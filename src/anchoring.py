"""Merkle batching and demo/Polygon anchoring support."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any

import db
from merkle import merkle_proof, merkle_root, verify_proof
from watchman_config import load_config


class AnchorService:
    def __init__(self) -> None:
        self.config = load_config()
        self.running = False
        self.thread: threading.Thread | None = None
        self.last_error: str | None = None

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._loop, name="watchman-anchor", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.running = False

    def run_once(self) -> str | None:
        alerts = db.get_pending_alerts()
        if not alerts:
            return None
        leaf_hashes = [alert["alert_hash"] for alert in alerts]
        root = merkle_root(leaf_hashes)
        if not root:
            return None
        batch_id = str(uuid.uuid4())
        for index, alert in enumerate(alerts):
            alert["merkle_proof"] = merkle_proof(leaf_hashes, index)
        status = "confirmed"
        tx_hash = None
        error = None
        try:
            tx_hash = self._anchor_root(batch_id, root, len(alerts))
        except Exception as exc:
            status = "failed"
            error = str(exc)
            self.last_error = error
        db.mark_batch(batch_id, alerts, root, status, tx_hash, error)
        return batch_id

    def verify_alert(self, alert: dict[str, Any]) -> dict[str, Any]:
        if alert["anchor_status"] != "confirmed":
            return {
                "verified": False,
                "reason": "not yet anchored" if alert["anchor_status"] == "pending" else alert["anchor_status"],
                "batch_id": alert.get("batch_id"),
                "merkle_root": alert.get("merkle_root"),
                "polygon_tx_hash": alert.get("polygon_tx_hash"),
            }
        ok = verify_proof(alert["alert_hash"], alert["merkle_proof"], alert["merkle_root"])
        return {
            "verified": ok,
            "reason": "verified" if ok else "tampered",
            "batch_id": alert.get("batch_id"),
            "merkle_root": alert.get("merkle_root"),
            "polygon_tx_hash": alert.get("polygon_tx_hash"),
        }

    def _loop(self) -> None:
        interval = int(self.config["blockchain"]["anchor_interval_seconds"])
        while self.running:
            self.run_once()
            time.sleep(max(1, interval))

    def _anchor_root(self, batch_id: str, root: str, alert_count: int) -> str | None:
        chain_cfg = self.config["blockchain"]
        if not chain_cfg.get("enabled") or chain_cfg.get("demo_mode", True):
            return f"demo:{batch_id}:{root[:16]}"
        private_key = __import__("os").getenv("WATCHMAN_PRIVATE_KEY")
        if not private_key:
            raise RuntimeError("WATCHMAN_PRIVATE_KEY is required when blockchain.enabled=true")
        try:
            from web3 import Web3
        except Exception as exc:
            raise RuntimeError("web3.py is required for live Polygon anchoring") from exc
        w3 = Web3(Web3.HTTPProvider(chain_cfg["polygon_rpc_url"]))
        if not w3.is_connected():
            raise RuntimeError("Cannot connect to Polygon RPC endpoint")
        # Contract wire-up is intentionally conservative: demo mode is the default, and
        # live mode requires a deployed contract with logRoot(bytes32,uint256,string).
        raise RuntimeError("Live Polygon anchoring needs deployed logRoot contract ABI wiring")
