import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
os.environ["WATCHMAN_DB_PATH"] = str(Path(__file__).resolve().parent / "test-alerts.db")

from fastapi.testclient import TestClient

import auth
import db
from app import app, anchor_service


def test_api_requires_auth_for_alerts():
    db.init_db()
    client = TestClient(app)

    response = client.get("/alerts")

    assert response.status_code == 401


def test_login_and_verify_unanchored_alert():
    db.init_db()
    db.upsert_user("api-test", auth.hash_password("secret123"), "superadmin")
    alert = db.insert_alert({
        "attack_type": "dos",
        "source_ip": "10.0.0.5",
        "destination_ip": "10.0.0.1",
        "source_port": 1234,
        "destination_port": 80,
        "confidence_score": 0.98,
        "protocol": "6",
    })
    client = TestClient(app)

    login = client.post("/auth/login", json={"username": "api-test", "password": "secret123"})
    token = login.json()["token"]
    verify = client.get(f"/verify/{alert['alert_id']}", headers={"Authorization": f"Bearer {token}"})

    assert login.status_code == 200
    assert verify.status_code == 200
    assert verify.json()["verified"] is False
    assert verify.json()["reason"] == "not yet anchored"


def test_anchor_then_verify_alert():
    db.init_db()
    db.upsert_user("anchor-test", auth.hash_password("secret123"), "superadmin")
    alert = db.insert_alert({
        "attack_type": "bruteforce",
        "source_ip": "10.0.0.7",
        "destination_ip": "10.0.0.1",
        "source_port": 2222,
        "destination_port": 22,
        "confidence_score": 0.96,
        "protocol": "6",
    })
    anchor_service.run_once()
    client = TestClient(app)
    login = client.post("/auth/login", json={"username": "anchor-test", "password": "secret123"})
    token = login.json()["token"]

    verify = client.get(f"/verify/{alert['alert_id']}", headers={"Authorization": f"Bearer {token}"})

    assert verify.status_code == 200
    assert verify.json()["verified"] is True


def test_manual_block_triggers_ips():
    db.init_db()
    db.upsert_user("ips-test", auth.hash_password("secret123"), "superadmin")
    alert = db.insert_alert({
        "attack_type": "dos",
        "source_ip": "192.168.9.9",
        "destination_ip": "10.0.0.1",
        "source_port": 1234,
        "destination_port": 80,
        "confidence_score": 0.98,
        "protocol": "6",
    })
    client = TestClient(app)
    login = client.post("/auth/login", json={"username": "ips-test", "password": "secret123"})
    token = login.json()["token"]

    response = client.put(
        f"/alerts/{alert['alert_id']}/status",
        json={"status": "blocked"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "blocked"

    import ips
    assert ips.is_blocked("192.168.9.9") is True

