"""
ganache_manager.py
WatchMan NIDS — Ganache CLI Manager

Starts Ganache CLI as a subprocess, deploys NIDSLogger contract
on first run, saves address to config. Subsequent runs reuse
the same deterministic accounts via fixed mnemonic.

REQUIRES:
  npm install -g ganache
  OR: npm install ganache (project-local)

DETERMINISTIC MODE:
  Fixed mnemonic → same 10 accounts every time
  → contract always deployed from accounts[0]
  → address saved to data/watchman.config.json
"""

import os
import sys
import json
import time
import subprocess
import threading
import logging
from pathlib import Path

from logger import logger as log

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────

BASE_DIR    = Path(__file__).parent.parent
CONFIG_FILE = BASE_DIR / 'data' / 'watchman.config.json'
CONTRACT_BUILD = BASE_DIR / 'blockchain' / 'build' / 'contracts' / 'NIDSLogger.json'

GANACHE_PORT     = 7545
GANACHE_HOST     = '127.0.0.1'
GANACHE_URL      = f'http://{GANACHE_HOST}:{GANACHE_PORT}'
GANACHE_CHAIN_ID = 1337
GANACHE_MNEMONIC = (
    'candy maple cake sugar pudding cream honey rich smooth crumble sweet treat'
)  # deterministic — same accounts every time

# ─────────────────────────────────────────────────────────────
# PROCESS MANAGER
# ─────────────────────────────────────────────────────────────

class GanacheManager:
    """
    Manages the Ganache CLI process lifecycle.
    Handles start, health check, contract deploy, and shutdown.
    """

    def __init__(self):
        self.process     = None
        self.url         = GANACHE_URL
        self.port        = GANACHE_PORT
        self.mnemonic    = GANACHE_MNEMONIC
        self.contract_address = None
        self.accounts    = []
        self.ready       = False
        self._log_thread = None

    # ── Start ──────────────────────────────────────────────

    def start(self, wait=True, timeout=15) -> bool:
        """
        Launch Ganache CLI as a subprocess.
        Returns True when ready, False on failure.
        """
        if self._is_running():
            log.info(f'Ganache already running at {self.url}')
            self.ready = True
            return True

        cmd = self._build_command()
        log.info(f'Starting Ganache CLI: {" ".join(cmd)}')

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout = subprocess.PIPE,
                stderr = subprocess.STDOUT,
                text   = True,
                bufsize= 1,
            )
        except FileNotFoundError:
            log.error(
                'ganache not found. Install it:\n'
                '  npm install -g ganache\n'
                '  OR: npm install ganache'
            )
            return False

        # Stream logs in background thread
        self._log_thread = threading.Thread(
            target = self._stream_logs,
            daemon = True
        )
        self._log_thread.start()

        if wait:
            return self._wait_until_ready(timeout)

        return True

    def _build_command(self) -> list:
        """Build Ganache CLI command with deterministic settings."""
        # Try local install first, then global
        ganache_bin = self._find_ganache_bin()

        cmd = [
            ganache_bin,
            '--port',     str(self.port),
            '--host',     GANACHE_HOST,
            '--mnemonic', self.mnemonic,
            '--chain.chainId', str(GANACHE_CHAIN_ID),
            '--accounts', '10',
            '--deterministic',
            '--quiet',    # suppress verbose account listing (we log separately)
        ]
        return cmd

    def _find_ganache_bin(self) -> str:
        """Find ganache binary — local node_modules or global."""
        # Local install
        local = BASE_DIR / 'node_modules' / '.bin' / 'ganache'
        local_cmd = str(local) + ('.cmd' if sys.platform == 'win32' else '')
        if Path(local_cmd).exists():
            return local_cmd

        local_plain = str(local)
        if Path(local_plain).exists():
            return local_plain

        # Global install
        return 'ganache.cmd' if sys.platform == 'win32' else 'ganache'

    def _stream_logs(self):
        """Read Ganache stdout and forward to logger."""
        for line in self.process.stdout:
            line = line.rstrip()
            if line:
                log.debug(f'[Ganache] {line}')

    def _wait_until_ready(self, timeout=15) -> bool:
        """Poll until Ganache responds to JSON-RPC."""
        import urllib.request
        import urllib.error

        log.info(f'Waiting for Ganache on {self.url}...')
        deadline = time.time() + timeout

        while time.time() < deadline:
            try:
                req  = urllib.request.Request(
                    self.url,
                    data    = json.dumps({'jsonrpc':'2.0','method':'eth_accounts','params':[],'id':1}).encode(),
                    headers = {'Content-Type': 'application/json'},
                )
                resp = urllib.request.urlopen(req, timeout=2)
                data = json.loads(resp.read())

                if 'result' in data:
                    self.accounts = data['result']
                    log.info(f'Ganache ready — {len(self.accounts)} accounts')
                    self.ready = True
                    return True

            except Exception:
                time.sleep(0.5)

        log.error(f'Ganache did not start within {timeout}s')
        return False

    def _is_running(self) -> bool:
        """Check if Ganache is already running at our port."""
        import urllib.request
        try:
            req = urllib.request.Request(
                self.url,
                data    = json.dumps({'jsonrpc':'2.0','method':'eth_chainId','params':[],'id':1}).encode(),
                headers = {'Content-Type': 'application/json'},
            )
            urllib.request.urlopen(req, timeout=2)
            return True
        except Exception:
            return False

    # ── Contract Deployment ────────────────────────────────

    def deploy_contract(self, force=False) -> str:
        """
        Deploy NIDSLogger contract if not already deployed.
        Returns contract address.
        Saves address to watchman.config.json.
        """
        # Check saved address
        cfg = self._load_config()
        saved_addr = cfg.get('contract_address')

        if saved_addr and not force:
            log.info(f'Reusing deployed contract at {saved_addr}')
            self.contract_address = saved_addr
            return saved_addr

        # Deploy fresh
        log.info('Deploying NIDSLogger contract...')
        try:
            from web3 import Web3
            from web3.middleware import ExtraDataToPOAMiddleware

            w3 = Web3(Web3.HTTPProvider(self.url))
            w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

            if not w3.is_connected():
                raise ConnectionError('Cannot connect to Ganache for deployment')

            # Load ABI + bytecode from build artifact
            if not CONTRACT_BUILD.exists():
                raise FileNotFoundError(
                    f'Contract build not found at {CONTRACT_BUILD}\n'
                    f'Run: cd blockchain && truffle compile'
                )

            with open(CONTRACT_BUILD) as f:
                artifact = json.load(f)

            abi      = artifact['abi']
            bytecode = artifact['bytecode']
            deployer = w3.eth.accounts[0]

            # Deploy
            Contract  = w3.eth.contract(abi=abi, bytecode=bytecode)
            tx_hash   = Contract.constructor().transact({
                'from' : deployer,
                'gas'  : 3_000_000,
            })
            receipt   = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
            address   = receipt.contractAddress

            log.info(f'Contract deployed at {address}')
            log.info(f'Gas used: {receipt.gasUsed}')

            # Save to config
            self.contract_address = address
            cfg['contract_address'] = address
            cfg['deployer_account'] = deployer
            cfg['ganache_url']      = self.url
            cfg['chain_id']         = GANACHE_CHAIN_ID
            self._save_config(cfg)

            # Also update blockchain/build artifact networks
            self._update_artifact_networks(artifact, abi, bytecode, address, w3)

            return address

        except Exception as e:
            log.error(f'Contract deployment failed: {e}')
            raise

    def _update_artifact_networks(self, artifact, abi, bytecode, address, w3):
        """Write deployed address back into the build artifact for truffle compatibility."""
        try:
            artifact['networks'] = artifact.get('networks', {})
            artifact['networks'][str(GANACHE_CHAIN_ID)] = {
                'address': address,
                'transactionHash': '',
            }
            with open(CONTRACT_BUILD, 'w') as f:
                json.dump(artifact, f, indent=2)
        except Exception as e:
            log.warning(f'Could not update artifact: {e}')

    # ── Stats ──────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Return Ganache runtime stats."""
        if not self.ready:
            return {'status': 'offline'}

        try:
            import urllib.request
            req  = urllib.request.Request(
                self.url,
                data    = json.dumps({'jsonrpc':'2.0','method':'eth_blockNumber','params':[],'id':1}).encode(),
                headers = {'Content-Type':'application/json'},
            )
            resp  = json.loads(urllib.request.urlopen(req, timeout=3).read())
            block = int(resp['result'], 16)

            return {
                'status'    : 'online',
                'url'       : self.url,
                'chain_id'  : GANACHE_CHAIN_ID,
                'block'     : block,
                'accounts'  : len(self.accounts),
                'contract'  : self.contract_address,
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    # ── Shutdown ───────────────────────────────────────────

    def stop(self):
        """Terminate Ganache CLI process."""
        if self.process:
            log.info('Stopping Ganache CLI...')
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
            self.ready   = False

    # ── Config helpers ─────────────────────────────────────

    def _load_config(self) -> dict:
        try:
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            if CONFIG_FILE.exists():
                return json.loads(CONFIG_FILE.read_text())
        except Exception:
            pass
        return {}

    def _save_config(self, cfg: dict):
        try:
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            CONFIG_FILE.write_text(json.dumps(cfg, indent=2))
        except Exception as e:
            log.error(f'Could not save config: {e}')


# ─────────────────────────────────────────────────────────────
# STANDALONE TEST
# ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import signal

    mgr = GanacheManager()

    def shutdown(sig, frame):
        log.info('Shutting down...')
        mgr.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)

    log.info('\n' + '='*50)
    log.info('  WatchMan — Ganache CLI Manager Test')
    log.info('='*50)

    if mgr.start():
        log.info(f'\n  Ganache ready at {mgr.url}')
        log.info(f'  Accounts: {len(mgr.accounts)}')

        addr = mgr.deploy_contract()
        log.info(f'  Contract: {addr}')

        stats = mgr.get_stats()
        log.info(f'  Stats: {stats}')

        log.info('\n  Press Ctrl+C to stop')
        while True:
            time.sleep(1)
    else:
        log.error('  Ganache failed to start')
        sys.exit(1)