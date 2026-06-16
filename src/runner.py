"""Compatibility launcher for the PRD-aligned WatchMan FastAPI runtime."""

from __future__ import annotations

import argparse

from app import main


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="WatchMan NIDS runtime")
    parser.add_argument("--mode", choices=["all", "dashboard", "live", "file"], default="all")
    parser.add_argument("--iface", default=None, help="Retained for compatibility; configure in watchman.config.json.")
    parser.add_argument("--file", default=None, help="Retained for compatibility.")
    parser.add_argument("--no-blockchain", action="store_true", help="Retained for compatibility.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.mode == "file":
        raise SystemExit("File scan mode moved to the ML scripts; the PRD runtime starts the API daemon.")
    main()
