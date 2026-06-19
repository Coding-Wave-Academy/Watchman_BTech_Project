"""Configuration loader for the PRD-aligned WatchMan runtime."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent

if os.name == "posix" and Path("/etc/watchman").exists():
    CONFIG_PATH = Path("/etc/watchman/watchman.config.json")
    DATA_DIR = Path("/var/lib/watchman")
    DB_PATH = DATA_DIR / "alerts.db"
    MODELS_DIR = Path("/opt/watchman/models")
    DASHBOARD_DIR = Path("/opt/watchman/app/dashboard/dist")
else:
    DATA_DIR = BASE_DIR / "data"
    MODELS_DIR = BASE_DIR / "models"
    DASHBOARD_DIR = BASE_DIR / "dashboard" / "dist"
    CONFIG_PATH = DATA_DIR / "watchman.config.json"
    DB_PATH = DATA_DIR / "alerts.db"


DEFAULT_CONFIG: dict[str, Any] = {
    "api": {
        "host": "0.0.0.0",
        "port": 5000,
        "debug": False,
        "jwt_secret": "change-this-watchman-secret-before-production",
        "token_expiry_hours": 24,
        "https_certfile": "",
        "https_keyfile": "",
    },
    "capture": {
        "interface": None,
        "promiscuous": True,
        "flow_timeout_seconds": 30,
    },
    "ml": {
        "model_path": "models/random_forest.pkl",
        "isolation_model_path": "models/isolation_forest.pkl",
        "label_encoder_path": "models/label_encoder.pkl",
        "features_path": "models/features_cicids.json",
        "confidence_threshold": 0.85,
        "isolation_threshold": -0.1,
    },
    "blockchain": {
        "enabled": True,
        "demo_mode": False,
        "anchor_interval_seconds": 60,
        "celo_rpc_url": "https://forno.celo-sepolia.celo-testnet.org",
        "contract_address": "0xcec6152e54424db74d22f1fab308b2b75a732ed8de213c48567c08f63a9a8f34",
        "contract_abi_path": "blockchain/build/contracts/NIDSLogger.json",
    },
    "bootstrap": {
        "admin_username": "admin",
        "admin_password": "watchman2026",
        "admin_role": "superadmin",
    },
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config() -> dict[str, Any]:
    """Load config, migrating older flat config files into the PRD shape."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        return deepcopy(DEFAULT_CONFIG)

    try:
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        raw = {}

    migrated: dict[str, Any] = {}
    is_legacy = (
        "iface" in raw
        or "ganache_url" in raw
        or ("blockchain" in raw and not isinstance(raw["blockchain"], dict))
    )
    if is_legacy:
        migrated = {
            "capture": {"interface": raw.get("iface") if raw.get("iface") != "Loopback" else None},
            "blockchain": {
                "enabled": bool(raw.get("blockchain", False)),
                "demo_mode": not bool(raw.get("blockchain", False)),
                "contract_address": raw.get("contract_address", ""),
            },
        }

        for legacy_key in ("iface", "blockchain", "ipsMode", "license", "deployer_account", "ganache_url", "chain_id", "contract_address"):
            raw.pop(legacy_key, None)

    config = _deep_merge(DEFAULT_CONFIG, _deep_merge(migrated, raw))
    env_secret = os.getenv("WATCHMAN_JWT_SECRET")
    if env_secret:
        config["api"]["jwt_secret"] = env_secret
    return config


def save_config(config: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")


def resolve_path(value: str | os.PathLike[str]) -> Path:
    path = Path(value)
    return path if path.is_absolute() else BASE_DIR / path
