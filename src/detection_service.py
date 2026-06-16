"""WatchMan daemon runtime: model loading, capture lifecycle, and alert fan-out."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

from src import db
from src.watchman_config import MODELS_DIR, load_config, resolve_path


class DetectionService:
    def __init__(self, broadcaster=None) -> None:
        self.config = load_config()
        self.broadcaster = broadcaster
        self.running = False
        self.started_at: float | None = None
        self.thread: threading.Thread | None = None
        self.flows_processed = 0
        self.model_status = "not loaded"
        self.last_error: str | None = None
        self._models: tuple[Any, Any, Any] | None = None

    def start(self) -> None:
        if self.running:
            return
        self._ensure_features_file()
        self._load_models()
        self.running = True
        self.started_at = time.time()
        db.set_state("daemon_running", True)
        self.thread = threading.Thread(target=self._capture_loop, name="watchman-capture", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.running = False
        db.set_state("daemon_running", False)

    def status(self) -> dict[str, Any]:
        uptime = int(time.time() - self.started_at) if self.started_at else 0
        return {
            "running": self.running,
            "uptime_seconds": uptime,
            "interface": self.config["capture"]["interface"],
            "flows_processed": self.flows_processed,
            "model_status": self.model_status,
            "last_error": self.last_error,
        }

    def handle_detection(self, alert: dict[str, Any]) -> dict[str, Any] | None:
        confidence = float(alert.get("confidence_score") or alert.get("rf_confidence") or 0)
        if confidence < float(self.config["ml"]["confidence_threshold"]):
            return None
        record = db.insert_alert(alert)
        self.flows_processed += 1
        if self.broadcaster:
            self.broadcaster(record)
        return record

    def _load_models(self) -> None:
        try:
            import predict

            rf, iso, le = predict.load_models(str(MODELS_DIR))
            self._models = (rf, iso, le)
            self.model_status = "loaded"
        except Exception as exc:
            self.last_error = str(exc)
            self.model_status = "unavailable"

    def _capture_loop(self) -> None:
        try:
            if not self._models:
                return
            import predict

            rf, iso, le = self._models
            predict.FLOW_TIMEOUT = int(self.config["capture"]["flow_timeout_seconds"])
            predict.CONFIDENCE_THRESHOLD = float(self.config["ml"]["confidence_threshold"])
            predict.ISOLATION_THRESHOLD = float(self.config["ml"]["isolation_threshold"])
            predict.start_live_capture(
                rf,
                iso,
                le,
                iface=self.config["capture"]["interface"],
                alert_callback=self.handle_detection,
            )
        except Exception as exc:
            self.last_error = str(exc)
        finally:
            self.running = False
            db.set_state("daemon_running", False)

    def _ensure_features_file(self) -> None:
        features_path = resolve_path(self.config["ml"]["features_path"])
        if features_path.exists():
            return
        try:
            import predict

            features = list(predict.extract_features(
                ("0.0.0.0", "0.0.0.0", 0, 0, 6),
                [],
            ).columns)
        except Exception:
            features = []
        if not features:
            features = [
                "Destination Port", "Flow Duration", "Total Fwd Packets",
                "Total Backward Packets", "Total Length of Fwd Packets",
                "Total Length of Bwd Packets",
            ]
        features_path.parent.mkdir(exist_ok=True)
        features_path.write_text(json.dumps(features, indent=2), encoding="utf-8")
