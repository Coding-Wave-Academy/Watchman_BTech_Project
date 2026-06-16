"""
blockchain.py
NIDS + ML + Blockchain Project — BTech
Python integration layer between NIDS alert engine and Ganache

PIPELINE:
  Alert dict from predict.py
      ↓
  BlockchainLogger.log_alert()
      ↓
  Web3.py encodes and sends transaction
      ↓
  NIDSLogger smart contract stores on Ganache
      ↓
  Transaction hash returned and stored locally
"""

import json
import time
import sqlite3
import hashlib
import os
from datetime import datetime
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

# ─────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────

import sys
from pathlib import Path

BASE_DIR         = Path(__file__).parent.parent
GANACHE_URL      = "http://127.0.0.1:7545"
CONTRACT_PATH    = str(BASE_DIR / "blockchain" / "build" / "contracts" / "NIDSLogger.json")
DB_PATH          = str(BASE_DIR / "data" / "alerts.db")
CONFIG_FILE      = BASE_DIR / "data" / "watchman.config.json"

def _load_watchman_config() -> dict:
    """Load saved config (contract address, etc.)."""
    try:
        if CONFIG_FILE.exists():
            return json.loads(CONFIG_FILE.read_text())
    except Exception:
        pass
    return {}

# ─────────────────────────────────────────────────────────────
# MODULE 1 — Connect to Ganache
# ─────────────────────────────────────────────────────────────

def connect_to_ganache(url=GANACHE_URL):
    """Establish Web3 connection to Ganache."""
    print("\n[MODULE 1] Connecting to Ganache...")

    w3 = Web3(Web3.HTTPProvider(url))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

    if not w3.is_connected():
        raise ConnectionError(f"Cannot connect to Ganache at {url}")

    print(f"  Connected : {url}")
    print(f"  Chain ID  : {w3.eth.chain_id}")
    print(f"  Accounts  : {len(w3.eth.accounts)}")
    print(f"  Balance   : {w3.from_wei(w3.eth.get_balance(w3.eth.accounts[0]), 'ether')} ETH")

    return w3

# ─────────────────────────────────────────────────────────────
# MODULE 2 — Load deployed contract
# ─────────────────────────────────────────────────────────────

def load_contract(w3, contract_path=CONTRACT_PATH):
    """Load the deployed NIDSLogger contract ABI and address."""
    print("\n[MODULE 2] Loading NIDSLogger contract...")

    with open(contract_path, 'r') as f:
        contract_json = json.load(f)

    abi = contract_json['abi']

    # Check watchman config first (set by ganache_manager.py on deploy)
    cfg     = _load_watchman_config()
    address = cfg.get('contract_address')

    if not address:
        # Fall back to build artifact networks
        networks = contract_json.get('networks', {})
        for net_id, net_data in networks.items():
            address = net_data.get('address')
            if address:
                break

    if not address:
        raise ValueError(
            "Contract not deployed.\n"
            "Run: python src/ganache_manager.py\n"
            "Or start runner.py which deploys automatically."
        )

    contract = w3.eth.contract(address=address, abi=abi)

    print(f"  Contract address : {address}")
    print(f"  Total alerts     : {contract.functions.getTotalAlerts().call()}")

    return contract, address

# ─────────────────────────────────────────────────────────────
# MODULE 3 — SQLite local backup
# ─────────────────────────────────────────────────────────────

def init_local_db(db_path=DB_PATH):
    """
    Initialise local SQLite database as backup to blockchain.
    Stores tx_hash for cross-referencing on-chain records.
    """
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp     TEXT NOT NULL,
            src_ip        TEXT,
            dst_ip        TEXT,
            src_port      INTEGER,
            dst_port      INTEGER,
            alert_type    TEXT,
            severity      TEXT,
            confidence    REAL,
            tx_hash       TEXT,
            block_number  INTEGER,
            on_chain_id   INTEGER,
            alert_hash    TEXT
        )
    ''')

    conn.commit()
    return conn

# ─────────────────────────────────────────────────────────────
# MAIN CLASS — BlockchainLogger
# ─────────────────────────────────────────────────────────────

class BlockchainLogger:
    """
    Receives alerts from predict.py and logs them to:
    1. Ganache blockchain (immutable, tamper-proof)
    2. Local SQLite database (fast querying for dashboard)
    """

    def __init__(self):
        self.w3         = None
        self.contract   = None
        self.account    = None
        self.db_conn    = None
        self.ready      = False

    def initialise(self, contract_address=None):
        """
        Connect to Ganache, load contract and local DB.
        contract_address: if provided, use this instead of reading from artifact/config.
        """
        print("\n" + "=" * 55)
        print("  BLOCKCHAIN LOGGER — INITIALISING")
        print("=" * 55)

        try:
            self.w3      = connect_to_ganache()
            self.account = self.w3.eth.accounts[0]

            # Load ABI from build artifact
            with open(CONTRACT_PATH, 'r') as f:
                artifact = json.load(f)
            abi = artifact['abi']

            # Resolve contract address — priority order:
            # 1. Passed directly from runner/ganache_manager (most reliable)
            # 2. watchman.config.json saved address
            # 3. Build artifact networks section
            addr = contract_address

            if not addr:
                # Try config file
                try:
                    import sys, os
                    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    cfg_path = os.path.join(base, 'data', 'watchman.config.json')
                    if os.path.exists(cfg_path):
                        with open(cfg_path) as cf:
                            cfg_data = json.load(cf)
                        addr = cfg_data.get('contract_address')
                except Exception:
                    pass

            if not addr:
                # Fall back to artifact
                for _, net in artifact.get('networks', {}).items():
                    addr = net.get('address')
                    if addr:
                        break

            if not addr:
                raise ValueError("No contract address found. Deploy first.")

            self.contract = self.w3.eth.contract(address=addr, abi=abi)

            # Verify contract is live with a simple call
            total = self.contract.functions.getTotalAlerts().call()

            self.db_conn = init_local_db()
            self.ready   = True

            print(f"  Contract address : {addr}")
            print(f"  Total alerts     : {total}")
            print(f"\n  Logging account  : {self.account}")
            print(f"  Logger ready     : YES")

        except Exception as e:
            print(f"\n  [ERROR] Blockchain init failed: {e}")
            print(f"  Falling back to local DB only")
            self.db_conn = init_local_db()
            self.ready   = False

        return self.ready

    def log_alert(self, alert: dict):
        """
        Main entry point — receives alert from predict.py.
        Logs to blockchain and local DB.
        """
        if not alert.get('is_attack'):
            return None

        src_ip     = alert.get('src_ip', '0.0.0.0')
        dst_ip     = alert.get('dst_ip', '0.0.0.0')
        src_port   = int(alert.get('src_port', 0))
        dst_port   = int(alert.get('dst_port', 0))
        alert_type = alert.get('label', 'Unknown')
        severity   = alert.get('severity', 'MEDIUM')
        confidence = int(alert.get('rf_confidence', 0) * 100)

        result = {
            'timestamp'    : alert.get('timestamp'),
            'src_ip'       : src_ip,
            'dst_ip'       : dst_ip,
            'src_port'     : src_port,
            'dst_port'     : dst_port,
            'alert_type'   : alert_type,
            'severity'     : severity,
            'confidence'   : confidence,
            'tx_hash'      : None,
            'block_number' : None,
            'on_chain_id'  : None,
            'alert_hash'   : None,
        }

        # ── Log to blockchain ──
        if self.ready:
            try:
                tx_result = self._log_to_chain(
                    src_ip, dst_ip, src_port, dst_port,
                    alert_type, severity, confidence
                )
                result.update(tx_result)
                print(f"  [CHAIN] Alert #{result['on_chain_id']} logged | tx: {result['tx_hash'][:20]}...")

            except Exception as e:
                print(f"  [CHAIN ERROR] {e} — saving to local DB only")

        # ── Always log to local DB ──
        self._log_to_db(result)

        return result

    def _log_to_chain(self, src_ip, dst_ip, src_port, dst_port,
                      alert_type, severity, confidence):
        """Send transaction to NIDSLogger smart contract."""

        tx = self.contract.functions.logAlert(
            src_ip,
            dst_ip,
            src_port,
            dst_port,
            alert_type,
            severity,
            confidence
        ).transact({
            'from' : self.account,
            'gas'  : 500000,
        })

        # Wait for transaction to be mined
        receipt = self.w3.eth.wait_for_transaction_receipt(tx)

        # Get on-chain alert ID from event logs
        logs = self.contract.events.AlertLogged().process_receipt(receipt)
        on_chain_id = logs[0]['args']['id'] if logs else None

        # Get alert hash from contract
        if on_chain_id:
            stored = self.contract.functions.getAlert(on_chain_id).call()
            alert_hash = stored[9].hex()   # alertHash field
        else:
            alert_hash = None

        return {
            'tx_hash'      : receipt['transactionHash'].hex(),
            'block_number' : receipt['blockNumber'],
            'on_chain_id'  : on_chain_id,
            'alert_hash'   : alert_hash,
        }

    def _log_to_db(self, result):
        """Save alert to local SQLite database."""
        cur = self.db_conn.cursor()
        cur.execute('''
            INSERT INTO alerts (
                timestamp, src_ip, dst_ip, src_port, dst_port,
                alert_type, severity, confidence,
                tx_hash, block_number, on_chain_id, alert_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            result['timestamp'],
            result['src_ip'],
            result['dst_ip'],
            result['src_port'],
            result['dst_port'],
            result['alert_type'],
            result['severity'],
            result['confidence'],
            result['tx_hash'],
            result['block_number'],
            result['on_chain_id'],
            result['alert_hash'],
        ))
        self.db_conn.commit()

    # ─────────────────────────────────────────────
    # VERIFICATION — key demo feature
    # ─────────────────────────────────────────────

    def verify_alert(self, on_chain_id):
        """
        Verify integrity of a stored alert.
        Calls contract's verifyAlert() function.
        This is the tamper detection demo moment.
        """
        if not self.ready:
            print("  [ERROR] Not connected to blockchain")
            return None

        is_valid = self.contract.functions.verifyAlert(on_chain_id).call()

        print(f"\n  [VERIFY] Alert #{on_chain_id}: {'VALID ✓' if is_valid else 'TAMPERED ✗'}")
        return is_valid

    def verify_all_alerts(self):
        """Verify integrity of every stored alert."""
        if not self.ready:
            return

        total   = self.contract.functions.getTotalAlerts().call()
        valid   = 0
        invalid = 0

        print(f"\n  Verifying {total} on-chain alerts...")

        for i in range(1, total + 1):
            result = self.contract.functions.verifyAlert(i).call()
            if result:
                valid += 1
            else:
                invalid += 1

        print(f"  Valid   : {valid}")
        print(f"  Tampered: {invalid}")
        print(f"  Integrity: {'100%' if invalid == 0 else f'{invalid} alerts compromised'}")

        return {'valid': valid, 'invalid': invalid}

    # ─────────────────────────────────────────────
    # QUERY FUNCTIONS — for dashboard
    # ─────────────────────────────────────────────

    def get_recent_alerts(self, limit=20):
        """Fetch recent alerts from local DB for dashboard."""
        cur = self.db_conn.cursor()
        cur.execute('''
            SELECT * FROM alerts
            ORDER BY id DESC
            LIMIT ?
        ''', (limit,))

        columns = [desc[0] for desc in cur.description]
        rows    = cur.fetchall()

        return [dict(zip(columns, row)) for row in rows]

    def get_alert_stats(self):
        """Get summary statistics for dashboard."""
        cur = self.db_conn.cursor()

        cur.execute('SELECT COUNT(*) FROM alerts')
        total = cur.fetchone()[0]

        cur.execute('SELECT alert_type, COUNT(*) FROM alerts GROUP BY alert_type')
        by_type = dict(cur.fetchall())

        cur.execute('SELECT severity, COUNT(*) FROM alerts GROUP BY severity')
        by_severity = dict(cur.fetchall())

        cur.execute('''
            SELECT src_ip, COUNT(*) as cnt
            FROM alerts
            GROUP BY src_ip
            ORDER BY cnt DESC
            LIMIT 5
        ''')
        top_attackers = cur.fetchall()

        return {
            'total'        : total,
            'by_type'      : by_type,
            'by_severity'  : by_severity,
            'top_attackers': top_attackers,
        }

    def get_chain_stats(self):
        """Get on-chain statistics directly from contract."""
        if not self.ready:
            return None

        total    = self.contract.functions.getTotalAlerts().call()
        balance  = self.w3.from_wei(
            self.w3.eth.get_balance(self.account), 'ether'
        )

        return {
            'total_on_chain' : total,
            'eth_balance'    : float(balance),
            'contract'       : self.contract.address,
            'account'        : self.account,
        }


# ─────────────────────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    logger = BlockchainLogger()
    logger.initialise()

    # Simulate a test alert
    test_alert = {
        'timestamp'     : datetime.utcnow().isoformat(),
        'src_ip'        : '192.168.1.105',
        'dst_ip'        : '192.168.1.1',
        'src_port'      : 4444,
        'dst_port'      : 22,
        'label'         : 'BruteForce',
        'severity'      : 'HIGH',
        'rf_confidence' : 0.97,
        'iso_score'     : 0.12,
        'packet_count'  : 120,
        'note'          : 'Test alert',
        'is_attack'     : True,
    }

    print("\n  Logging test alert...")
    result = logger.log_alert(test_alert)

    if result and result.get('on_chain_id'):
        print(f"\n  Verifying integrity...")
        logger.verify_alert(result['on_chain_id'])

    print(f"\n  Chain stats:")
    stats = logger.get_chain_stats()
    if stats:
        for k, v in stats.items():
            print(f"    {k}: {v}")