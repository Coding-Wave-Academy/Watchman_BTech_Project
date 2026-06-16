"""
ips.py
WatchMan NIDS — Intrusion Prevention System (IPS)
Premium feature: blocks attacking IPs via iptables

MODES:
  - enforce  : real iptables rules (requires root / sudo)
  - simulate : logs what would happen, no actual blocking
              (safe for demo / Windows dev machines)

CALLED BY:
  - runner.py AlertPipeline._check_ips()  (auto-block)
  - app.py    /api/ips/block              (manual block)
"""

import subprocess
import platform
import sqlite3
import os
from datetime import datetime, timezone
from src.logger import logger as log

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────

DB_PATH         = 'data/alerts.db'
SIMULATE        = (platform.system() != 'Linux')   # auto-simulate on Windows/Mac
BAN_DURATION_H  = 24                               # hours before auto-unblock
IPTABLES_CHAIN  = 'WATCHMAN_IPS'                   # custom chain name

# ─────────────────────────────────────────────────────────────
# IPTABLES CHAIN SETUP
# ─────────────────────────────────────────────────────────────

def setup_chain():
    """
    Create WATCHMAN_IPS chain and hook it into INPUT.
    Safe to call multiple times — skips if already exists.
    Called once at IPS initialisation.
    """
    global SIMULATE
    if SIMULATE:
        log.info('[IPS] Simulate mode — skipping iptables chain setup')
        return {'success': True, 'mode': 'simulate'}

    try:
        # Create chain (ignore error if already exists)
        subprocess.run(
            ['iptables', '-N', IPTABLES_CHAIN],
            capture_output=True
        )

        # Check if chain is already hooked into INPUT
        check = subprocess.run(
            ['iptables', '-C', 'INPUT', '-j', IPTABLES_CHAIN],
            capture_output=True
        )

        # Hook chain into INPUT if not already there
        if check.returncode != 0:
            subprocess.run(
                ['iptables', '-I', 'INPUT', '1', '-j', IPTABLES_CHAIN],
                check=True, capture_output=True
            )

        log.info(f'[IPS] Chain {IPTABLES_CHAIN} ready')
        return {'success': True, 'mode': 'enforce'}

    except subprocess.CalledProcessError as e:
        log.error(f'[IPS] Chain setup failed: {e}')
        return {'success': False, 'error': str(e)}
    except FileNotFoundError:
        log.warning('[IPS] iptables not found — switching to simulate mode')
        SIMULATE = True
        return {'success': True, 'mode': 'simulate'}

# ─────────────────────────────────────────────────────────────
# BLOCK / UNBLOCK
# ─────────────────────────────────────────────────────────────

def block_ip(ip: str, reason: str = 'Manual block', blocked_by: str = 'system') -> dict:
    """
    Block an IP address.
    - Adds iptables DROP rule (enforce mode)
    - Records in SQLite blocked_ips table
    - Returns result dict
    """
    if not _is_valid_ip(ip):
        return {'success': False, 'error': f'Invalid IP: {ip}'}

    # Check if already blocked
    if _is_blocked(ip):
        return {'success': True, 'already_blocked': True, 'ip': ip}

    # Apply iptables rule
    iptables_result = _iptables_block(ip)

    # Record in DB regardless of iptables result
    _record_block(ip, reason, blocked_by)

    mode = 'simulate' if SIMULATE else 'enforce'
    log.warning(f'[IPS] BLOCKED {ip} | reason={reason} | mode={mode}')

    return {
        'success'   : True,
        'ip'        : ip,
        'reason'    : reason,
        'mode'      : mode,
        'iptables'  : iptables_result,
    }


def unblock_ip(ip: str) -> dict:
    """
    Remove an IP block.
    - Removes iptables DROP rule
    - Deletes from SQLite blocked_ips table
    """
    if not _is_valid_ip(ip):
        return {'success': False, 'error': f'Invalid IP: {ip}'}

    # Remove iptables rule
    iptables_result = _iptables_unblock(ip)

    # Remove from DB
    _record_unblock(ip)

    log.info(f'[IPS] UNBLOCKED {ip}')

    return {
        'success'  : True,
        'ip'       : ip,
        'iptables' : iptables_result,
    }


def get_blocked_ips() -> list:
    """Return all currently blocked IPs from DB."""
    try:
        import db
        conn = db.connect()
        rows = conn.execute(
            'SELECT * FROM blocked_ips ORDER BY id DESC'
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        log.error(f'[IPS] get_blocked_ips failed: {e}')
        return []


def is_blocked(ip: str) -> bool:
    """Quick check — is this IP currently blocked?"""
    return _is_blocked(ip)


def list_iptables_rules() -> list:
    """Return active WATCHMAN_IPS chain rules (enforce mode only)."""
    if SIMULATE:
        blocked = get_blocked_ips()
        return [f"SIMULATE DROP {r['ip']}" for r in blocked]

    try:
        result = subprocess.run(
            ['iptables', '-L', IPTABLES_CHAIN, '-n', '--line-numbers'],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip().split('\n')
    except Exception as e:
        log.error(f'[IPS] list rules failed: {e}')
        return []

# ─────────────────────────────────────────────────────────────
# IPTABLES HELPERS
# ─────────────────────────────────────────────────────────────

def _iptables_block(ip: str) -> dict:
    if SIMULATE:
        log.info(f'[IPS:SIM] Would run: iptables -I {IPTABLES_CHAIN} -s {ip} -j DROP')
        return {'simulated': True, 'command': f'iptables -I {IPTABLES_CHAIN} -s {ip} -j DROP'}

    try:
        subprocess.run(
            ['iptables', '-I', IPTABLES_CHAIN, '-s', ip, '-j', 'DROP'],
            check=True, capture_output=True
        )
        return {'applied': True}
    except subprocess.CalledProcessError as e:
        log.error(f'[IPS] iptables block failed for {ip}: {e}')
        return {'applied': False, 'error': str(e)}
    except FileNotFoundError:
        log.warning('[IPS] iptables not found')
        return {'applied': False, 'error': 'iptables not found'}


def _iptables_unblock(ip: str) -> dict:
    if SIMULATE:
        log.info(f'[IPS:SIM] Would run: iptables -D {IPTABLES_CHAIN} -s {ip} -j DROP')
        return {'simulated': True}

    try:
        subprocess.run(
            ['iptables', '-D', IPTABLES_CHAIN, '-s', ip, '-j', 'DROP'],
            check=True, capture_output=True
        )
        return {'removed': True}
    except subprocess.CalledProcessError as e:
        log.error(f'[IPS] iptables unblock failed for {ip}: {e}')
        return {'removed': False, 'error': str(e)}

# ─────────────────────────────────────────────────────────────
# DB HELPERS
# ─────────────────────────────────────────────────────────────

def _record_block(ip: str, reason: str, blocked_by: str):
    try:
        import db
        conn = db.connect()
        conn.execute('''
            INSERT OR REPLACE INTO blocked_ips
            (ip, reason, blocked_at, blocked_by)
            VALUES (?, ?, ?, ?)
        ''', (
            ip, reason,
            datetime.now(timezone.utc).isoformat(),
            blocked_by
        ))
        # Mark all alerts from this IP as blocked
        conn.execute(
            "UPDATE alerts_v2 SET status = 'blocked' WHERE source_ip = ?", (ip,)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        log.error(f'[IPS] DB record_block failed: {e}')


def _record_unblock(ip: str):
    try:
        import db
        conn = db.connect()
        conn.execute('DELETE FROM blocked_ips WHERE ip = ?', (ip,))
        conn.execute(
            "UPDATE alerts_v2 SET status = 'active' WHERE source_ip = ?", (ip,)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        log.error(f'[IPS] DB record_unblock failed: {e}')


def _is_blocked(ip: str) -> bool:
    try:
        import db
        conn  = db.connect()
        count = conn.execute(
            'SELECT COUNT(*) FROM blocked_ips WHERE ip = ?', (ip,)
        ).fetchone()[0]
        conn.close()
        return count > 0
    except Exception:
        return False

# ─────────────────────────────────────────────────────────────
# VALIDATION
# ─────────────────────────────────────────────────────────────

def _is_valid_ip(ip: str) -> bool:
    """Basic IPv4 validation."""
    import re
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(pattern, ip):
        return False
    parts = ip.split('.')
    return all(0 <= int(p) <= 255 for p in parts)

# ─────────────────────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    log.info('\n' + '=' * 50)
    log.info('  WatchMan IPS — Module Test')
    log.info(f'  Mode: {"SIMULATE" if SIMULATE else "ENFORCE (iptables)"}')
    log.info('=' * 50)

    # Test block
    log.info('\n[TEST 1] Blocking 192.168.1.99...')
    result = block_ip('192.168.1.99', reason='Test block', blocked_by='test')
    log.info(f'  Result: {result}')

    # Test double-block
    log.info('\n[TEST 2] Double-blocking same IP...')
    result = block_ip('192.168.1.99', reason='Test duplicate')
    log.info(f'  Result: {result}')

    # Test list
    log.info('\n[TEST 3] Listing blocked IPs...')
    blocked = get_blocked_ips()
    for b in blocked:
        log.info(f'  {b["ip"]} — {b["reason"]} — {b["blocked_at"]}')

    # Test iptables rules
    log.info('\n[TEST 4] Active iptables rules...')
    rules = list_iptables_rules()
    for r in rules:
        log.info(f'  {r}')

    # Test unblock
    log.info('\n[TEST 5] Unblocking 192.168.1.99...')
    result = unblock_ip('192.168.1.99')
    log.info(f'  Result: {result}')

    log.info('\nIPS module test complete.\n')
