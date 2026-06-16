"""FastAPI entrypoint for the PRD-aligned WatchMan NIDS."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import jwt
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src import auth
from src import db
from src.anchoring import AnchorService
from src.detection_service import DetectionService
from src.watchman_config import BASE_DIR, DASHBOARD_DIR, load_config


config = load_config()
docs_url = "/docs" if config["api"].get("debug") else None
openapi_url = "/openapi.json" if config["api"].get("debug") else None

@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    auth.bootstrap_admin()
    anchor_service.start()
    detection_service.start()
    yield
    detection_service.stop()
    anchor_service.stop()

app = FastAPI(
    title="WatchMan NIDS API",
    version="1.0.0",
    docs_url=docs_url,
    redoc_url=None,
    openapi_url=openapi_url,
    lifespan=lifespan,
)

security = HTTPBearer()
websocket_clients: set[WebSocket] = set()
anchor_service = AnchorService()
detection_service = DetectionService()


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: dict[str, Any]


class StatusUpdate(BaseModel):
    status: str


def _broadcast_alert(alert: dict[str, Any]) -> None:
    async def send() -> None:
        stale: list[WebSocket] = []
        for ws in websocket_clients:
            try:
                await ws.send_json({"type": "alert", "alert": alert})
            except Exception:
                stale.append(ws)
        for ws in stale:
            websocket_clients.discard(ws)

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(send())
    except RuntimeError:
        pass


detection_service.broadcaster = _broadcast_alert





@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "watchman-api"}


def current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict[str, Any]:
    try:
        payload = auth.decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Token expired. Log in again.") from exc
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid bearer token.") from exc
    user = db.get_user(payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="User no longer exists.")
    return user


def require_role(required: str):
    def dependency(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
        if not auth.role_allows(user["role"], required):
            raise HTTPException(status_code=403, detail=f"{required} role required.")
        return user

    return dependency


@app.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    user = db.get_user(payload.username)
    if not user or not auth.verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    token = auth.create_token(user["username"], user["role"])
    return LoginResponse(token=token, user={"username": user["username"], "role": user["role"]})


@app.get("/alerts")
def list_alerts(
    limit: int = Query(50, ge=1, le=500),
    attack_type: str | None = None,
    hours: int | None = Query(None, ge=1, le=24 * 365),
    _: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    return {"alerts": db.list_alerts(limit=limit, attack_type=attack_type, hours=hours)}


@app.get("/alerts/stats")
def alert_stats(_: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    return db.stats()


@app.get("/alerts/{alert_id}")
def get_alert(alert_id: str, _: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    alert = db.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")
    return alert


@app.put("/alerts/{alert_id}/status")
def update_alert_status(
    alert_id: str,
    payload: StatusUpdate,
    _: dict[str, Any] = Depends(require_role("admin")),
) -> dict[str, Any]:
    alert = db.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")
    conn = db.connect()
    conn.execute("UPDATE alerts_v2 SET status=? WHERE alert_id=?", (payload.status, alert_id))
    conn.commit()
    conn.close()

    source_ip = alert.get("source_ip")
    if source_ip:
        from src import ips
        if payload.status == "blocked":
            ips.block_ip(source_ip, reason=f"Alert {alert_id} marked as blocked", blocked_by="admin")
        elif payload.status == "active" and alert.get("status") == "blocked":
            ips.unblock_ip(source_ip)

    return db.get_alert(alert_id) or {"alert_id": alert_id, "status": payload.status}


@app.get("/alerts/trends")
def alert_trends(_: dict[str, Any] = Depends(current_user)) -> list[dict[str, Any]]:
    return db.get_trends()


@app.get("/system/status")
def system_status(_: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    return {
        "daemon": detection_service.status(),
        "alerts": db.stats(),
        "blockchain": {
            "enabled": config["blockchain"]["enabled"],
            "demo_mode": config["blockchain"]["demo_mode"],
            "anchor_interval_seconds": config["blockchain"]["anchor_interval_seconds"],
            "last_error": anchor_service.last_error,
        },
    }

@app.get("/system/ledger")
def system_ledger(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _: dict[str, Any] = Depends(current_user)
) -> dict[str, Any]:
    return db.get_ledger(limit, offset)

@app.get("/system/topology")
def system_topology(_: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    return db.get_topology()


@app.post("/system/start")
def system_start(_: dict[str, Any] = Depends(require_role("admin"))) -> dict[str, Any]:
    detection_service.start()
    return detection_service.status()


@app.post("/system/stop")
def system_stop(_: dict[str, Any] = Depends(require_role("admin"))) -> dict[str, Any]:
    detection_service.stop()
    return detection_service.status()


@app.post("/system/anchor")
def run_anchor_now(_: dict[str, Any] = Depends(require_role("admin"))) -> dict[str, Any]:
    batch_id = anchor_service.run_once()
    return {"batch_id": batch_id, "message": "no pending alerts" if not batch_id else "batch anchored"}


@app.get("/verify/{alert_id}")
def verify_alert(alert_id: str, _: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    alert = db.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")
    result = anchor_service.verify_alert(alert)
    return {"alert_id": alert_id, **result}


@app.websocket("/ws/alerts")
async def alerts_ws(websocket: WebSocket, token: str = Query("")) -> None:
    try:
        auth.decode_token(token)
    except Exception:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    websocket_clients.add(websocket)
    try:
        await websocket.send_json({"type": "hello", "message": "WatchMan alert stream connected"})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_clients.discard(websocket)


dashboard_assets = DASHBOARD_DIR / "assets"
if dashboard_assets.exists():
    app.mount("/assets", StaticFiles(directory=str(dashboard_assets)), name="assets")


@app.get("/")
def dashboard() -> FileResponse:
    return FileResponse(str(DASHBOARD_DIR / "index.html"))


@app.get("/{path:path}")
def spa_fallback(path: str) -> FileResponse:
    requested = DASHBOARD_DIR / path
    if requested.exists() and requested.is_file():
        return FileResponse(str(requested))
    return FileResponse(str(DASHBOARD_DIR / "index.html"))


def main() -> None:
    try:
        import uvicorn
    except Exception as exc:
        raise RuntimeError("uvicorn is required to run the WatchMan API") from exc
    uvicorn.run(
        "app:app",
        host=config["api"]["host"],
        port=int(config["api"]["port"]),
        reload=bool(config["api"].get("debug")),
        app_dir=str(BASE_DIR / "src"),
    )


if __name__ == "__main__":
    main()
