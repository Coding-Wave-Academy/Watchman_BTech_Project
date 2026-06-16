"""JWT and bcrypt auth helpers for WatchMan FastAPI."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

import db
from watchman_config import load_config


ALGORITHM = "HS256"
ROLE_ORDER = {"viewer": 1, "admin": 2, "superadmin": 3}


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def bootstrap_admin() -> None:
    config = load_config()
    username = config["bootstrap"]["admin_username"]
    if db.get_user(username):
        return
    db.upsert_user(
        username,
        hash_password(config["bootstrap"]["admin_password"]),
        config["bootstrap"].get("admin_role", "superadmin"),
    )


def create_token(username: str, role: str) -> str:
    config = load_config()
    expires = datetime.now(timezone.utc) + timedelta(hours=config["api"]["token_expiry_hours"])
    payload: dict[str, Any] = {"sub": username, "role": role, "exp": expires}
    return jwt.encode(payload, config["api"]["jwt_secret"], algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    config = load_config()
    return jwt.decode(token, config["api"]["jwt_secret"], algorithms=[ALGORITHM])


def role_allows(actual: str, required: str) -> bool:
    return ROLE_ORDER.get(actual, 0) >= ROLE_ORDER.get(required, 0)
