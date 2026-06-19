"""WatchMan command-line interface."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from src import auth
from src import db
from src.anchoring import AnchorService
from src.watchman_config import BASE_DIR, load_config, save_config


app = typer.Typer(help="WatchMan NIDS operations CLI")
console = Console()


def _api_base() -> str:
    cfg = load_config()
    return f"http://127.0.0.1:{cfg['api']['port']}"


def _token_path() -> Path:
    from src.watchman_config import DATA_DIR
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / ".watchman_token"


def _read_token() -> str | None:
    path = _token_path()
    try:
        return path.read_text(encoding="utf-8").strip() if path.exists() else None
    except PermissionError:
        console.print("[yellow]Warning: Could not read authentication token due to permission denied. Some commands may fail. Try running with sudo.[/yellow]")
        return None

def _api(path: str, method: str = "GET", body: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        import requests
    except Exception as exc:
        raise typer.BadParameter("requests is required for API-backed CLI commands") from exc
    headers = {}
    token = _read_token()
    if not token:
        # Auto-login if we can't read the saved token (e.g. non-root user)
        try:
            cfg = load_config()
            login_body = {
                "username": cfg["bootstrap"]["admin_username"],
                "password": cfg["bootstrap"]["admin_password"],
            }
            login_resp = requests.post(_api_base() + "/auth/login", json=login_body, timeout=10)
            if login_resp.status_code == 200:
                token = login_resp.json().get("token")
        except Exception:
            pass
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.request(method, _api_base() + path, json=body, headers=headers, timeout=10)
    if response.status_code == 401:
        # Token might be expired, try to auto-login and retry
        try:
            cfg = load_config()
            login_body = {
                "username": cfg["bootstrap"]["admin_username"],
                "password": cfg["bootstrap"]["admin_password"],
            }
            login_resp = requests.post(_api_base() + "/auth/login", json=login_body, timeout=10)
            if login_resp.status_code == 200:
                token = login_resp.json().get("token")
                try:
                    _token_path().write_text(token, encoding="utf-8")
                except Exception:
                    pass
                headers["Authorization"] = f"Bearer {token}"
                response = requests.request(method, _api_base() + path, json=body, headers=headers, timeout=10)
        except Exception:
            pass

    if response.status_code >= 400:
        raise typer.BadParameter(f"{response.status_code}: {response.text}")
    return response.json()


@app.command()
def install(
    username: str = typer.Option("admin", help="Bootstrap administrator username."),
    password: str = typer.Option("watchman2026", help="Bootstrap administrator password."),
) -> None:
    """Initialise DB, create admin user, and save a local session token."""
    db.init_db()
    db.upsert_user(username, auth.hash_password(password), "superadmin")
    token = auth.create_token(username, "superadmin")
    _token_path().write_text(token, encoding="utf-8")
    cfg = load_config()
    cfg["bootstrap"]["admin_username"] = username
    save_config(cfg)
    console.print("[green]WatchMan installed.[/green]")
    console.print(f"Admin user: [bold]{username}[/bold]")


@app.command()
def start() -> None:
    """Start the WatchMan daemon."""
    import os
    if os.name == "posix" and getattr(os, "geteuid", lambda: 0)() != 0:
        console.print("[red]Error: Root privileges required to start the daemon. Use 'sudo watchman start'[/red]")
        raise typer.Exit(1)
        
    console.print("Starting WatchMan daemon...")
    try:
        subprocess.run(["systemctl", "start", "watchman"], check=True, capture_output=True)
        console.print("[green]Service started via systemd.[/green]")
        console.print("Dashboard is now available at http://127.0.0.1:5000")
    except Exception:
        console.print("[yellow]Systemd not found or failed. Starting API server in the foreground...[/yellow]")
        cfg = load_config()
        console.print(f"Starting WatchMan API on http://127.0.0.1:{cfg['api']['port']}")
        try:
            process = subprocess.Popen([sys.executable, str(BASE_DIR / "src" / "app.py")], cwd=str(BASE_DIR))
            process.wait()
        except KeyboardInterrupt:
            console.print("\nShutting down WatchMan API...")
            process.terminate()
            process.wait()

@app.command()
def configure() -> None:
    """Show or edit the current configuration."""
    cfg = load_config()
    console.print_json(json.dumps(cfg, indent=2))
    console.print("Note: To edit configuration, modify /etc/watchman/watchman.config.json")


@app.command()
def stop() -> None:
    """Stop the WatchMan daemon."""
    console.print("Stopping WatchMan daemon...")
    try:
        subprocess.run(["systemctl", "stop", "watchman"], check=True)
        console.print("[green]Service stopped via systemd.[/green]")
    except Exception:
        console.print("[yellow]Systemd not found or permission denied. Stopping packet capture via API instead.[/yellow]")
        console.print_json(json.dumps(_api("/system/stop", method="POST")))

@app.command()
def restart() -> None:
    """Restart the WatchMan daemon."""
    console.print("Restarting WatchMan daemon...")
    try:
        subprocess.run(["systemctl", "restart", "watchman"], check=True)
        console.print("[green]Service restarted via systemd.[/green]")
    except Exception as e:
        console.print(f"[red]Failed to restart service: {e}[/red]")

@app.command()
def update() -> None:
    """Update WatchMan to the latest version."""
    console.print("Fetching updates...")
    subprocess.run(["git", "pull"])
    console.print("Updating dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    console.print("[green]Update complete. Please run `watchman restart` to apply changes.[/green]")

@app.command()
def uninstall() -> None:
    """Uninstall WatchMan from the system."""
    console.print("[red]To completely remove WatchMan, please run the uninstall.sh script with sudo privileges.[/red]")
    console.print("Example: sudo ./uninstall.sh")

@app.command()
def status() -> None:
    """Display daemon, model, alert, and blockchain health."""
    data = _api("/system/status")
    table = Table(title="WatchMan Status")
    table.add_column("Field")
    table.add_column("Value")
    daemon = data["daemon"]
    table.add_row("Running", str(daemon["running"]))
    table.add_row("Uptime", f"{daemon['uptime_seconds']}s")
    table.add_row("Interface", str(daemon["interface"]))
    table.add_row("Model", daemon["model_status"])
    table.add_row("Alerts", str(data["alerts"]["total_alerts"]))
    table.add_row("Confirmed anchors", str(data["alerts"]["confirmed_anchors"]))
    table.add_row("Blockchain", "demo" if data["blockchain"]["demo_mode"] else "live")
    console.print(table)


@app.command()
def monitor(interval: int = typer.Option(2, help="Refresh interval in seconds.")) -> None:
    """Stream recent alerts to the terminal."""
    console.print("[cyan]Monitoring for network intrusions... (Press Ctrl+C to stop)[/cyan]")
    seen: set[str] = set()
    while True:
        payload = _api("/alerts?limit=10")
        for alert in reversed(payload["alerts"]):
            if alert["alert_id"] in seen:
                continue
            seen.add(alert["alert_id"])
            console.print(
                f"[red]{alert['attack_type']}[/red] "
                f"{alert.get('source_ip')} -> {alert.get('destination_ip')} "
                f"conf={alert['confidence_score']:.2f} id={alert['alert_id']}"
            )
        time.sleep(interval)


@app.command("alerts")
def alerts_cmd(
    limit: int = typer.Option(20),
    attack_type: str | None = typer.Option(None),
    hours: int | None = typer.Option(None),
) -> None:
    """List alerts with PRD filters."""
    query = f"/alerts?limit={limit}"
    if attack_type:
        query += f"&attack_type={attack_type}"
    if hours:
        query += f"&hours={hours}"
    payload = _api(query)
    table = Table(title="WatchMan Alerts")
    for col in ("ID", "Time", "Type", "Source", "Destination", "Confidence", "Anchor"):
        table.add_column(col)
    for alert in payload["alerts"]:
        table.add_row(
            alert["alert_id"][:12],
            alert["timestamp"],
            alert["attack_type"],
            str(alert.get("source_ip")),
            str(alert.get("destination_ip")),
            f"{alert['confidence_score']:.2f}",
            alert["anchor_status"],
        )
    console.print(table)


@app.command()
def verify(alert_id: str) -> None:
    """Verify one alert's Merkle/blockchain proof."""
    result = _api(f"/verify/{alert_id}")
    color = "green" if result["verified"] else "red"
    console.print(f"[{color}]{result['reason']}[/{color}] alert={alert_id}")
    console.print_json(json.dumps(result))


@app.command()
def anchor() -> None:
    """Run one anchor cycle now."""
    import os
    if os.name == "posix" and getattr(os, "geteuid", lambda: 0)() != 0:
        console.print("[red]Error: Root privileges required to anchor alerts because it writes to the system database.[/red]")
        sys.exit(1)
        
    batch_id = AnchorService().run_once()
    console.print(batch_id or "No pending alerts.")


if __name__ == "__main__":
    app()
