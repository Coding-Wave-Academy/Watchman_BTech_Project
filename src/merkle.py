"""Deterministic alert hashing and Merkle proof utilities."""

from __future__ import annotations

import hashlib
import json
from typing import Any


HASH_FIELDS = (
    "alert_id",
    "timestamp",
    "attack_type",
    "source_ip",
    "destination_ip",
    "source_port",
    "destination_port",
    "confidence_score",
    "protocol",
)


def canonical_alert(alert: dict[str, Any]) -> dict[str, Any]:
    return {field: alert.get(field) for field in HASH_FIELDS}


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_alert_hash(alert: dict[str, Any]) -> str:
    payload = json.dumps(canonical_alert(alert), sort_keys=True, separators=(",", ":"))
    return sha256_hex("\x00" + payload)


def _pair_hash(left: str, right: str) -> str:
    return sha256_hex("\x01" + left + right)


def build_merkle_tree(leaf_hashes: list[str]) -> list[list[str]]:
    if not leaf_hashes:
        return []
    levels = [leaf_hashes[:]]
    while len(levels[-1]) > 1:
        current = levels[-1]
        next_level: list[str] = []
        for index in range(0, len(current), 2):
            left = current[index]
            right = current[index + 1] if index + 1 < len(current) else left
            next_level.append(_pair_hash(left, right))
        levels.append(next_level)
    return levels


def merkle_root(leaf_hashes: list[str]) -> str | None:
    tree = build_merkle_tree(leaf_hashes)
    return tree[-1][0] if tree else None


def merkle_proof(leaf_hashes: list[str], index: int) -> list[dict[str, str]]:
    tree = build_merkle_tree(leaf_hashes)
    if not tree:
        return []
    proof: list[dict[str, str]] = []
    cursor = index
    for level in tree[:-1]:
        sibling_index = cursor ^ 1
        if sibling_index >= len(level):
            sibling_index = cursor
        proof.append({
            "position": "left" if sibling_index < cursor else "right",
            "hash": level[sibling_index],
        })
        cursor //= 2
    return proof


def verify_proof(leaf_hash: str, proof: list[dict[str, str]], expected_root: str) -> bool:
    current = leaf_hash
    for item in proof:
        sibling = item["hash"]
        if item["position"] == "left":
            current = _pair_hash(sibling, current)
        else:
            current = _pair_hash(current, sibling)
    return current == expected_root
