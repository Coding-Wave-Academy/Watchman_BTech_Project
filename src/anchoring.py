"""Merkle batching and demo/Polygon anchoring support."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any

from src import db
from src.merkle import merkle_proof, merkle_root, verify_proof
from src.watchman_config import load_config


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
        
        import os
        # Manual dotenv parsing
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        k, v = line.strip().split('=', 1)
                        os.environ[k] = v.strip().strip('"').strip("'")

        private_key = os.getenv("WATCHMAN_PRIVATE_KEY")
        if not private_key:
            raise RuntimeError("WATCHMAN_PRIVATE_KEY is required when blockchain.enabled=true")
        
        try:
            from web3 import Web3
            from web3.middleware import ExtraDataToPOAMiddleware
        except Exception as exc:
            raise RuntimeError("web3.py is required for live Celo anchoring") from exc
        
        w3 = Web3(Web3.HTTPProvider(chain_cfg.get("celo_rpc_url", "https://forno.celo-sepolia.celo-testnet.org")))
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        
        if not w3.is_connected():
            raise RuntimeError("Cannot connect to Celo RPC endpoint")

        contract_addr = chain_cfg.get("contract_address")
        if not contract_addr or not contract_addr.startswith("0x"):
            raise RuntimeError("Valid 0x contract_address is required in watchman.config.json")
        
        import json
        abi_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "blockchain", "build", "contracts", "WatchmanAnchor.json")
        with open(abi_path) as f:
            abi = json.load(f)["abi"]

        account = w3.eth.account.from_key(private_key)
        contract = w3.eth.contract(address=contract_addr, abi=abi)

        tx = contract.functions.logRoot(batch_id, alert_count, root).build_transaction({
            'from': account.address,
            'nonce': w3.eth.get_transaction_count(account.address),
            'gas': 2000000,
            'gasPrice': w3.eth.gas_price
        })

        signed_tx = w3.eth.account.sign_transaction(tx, private_key=private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status != 1:
            raise RuntimeError("Transaction failed on-chain")
            
        return f"0x{tx_hash.hex()}"
