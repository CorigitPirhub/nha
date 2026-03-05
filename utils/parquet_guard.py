from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Mapping

from utils.artifact_hash import sha256_file

INPUTS_SHA256_FILENAME = "inputs_parquet_sha256.json"


def _stable_map(d: Mapping[str, str]) -> dict[str, str]:
    return {str(k): str(d[k]) for k in sorted(d.keys(), key=lambda x: str(x))}


def compute_sha256_map(paths: Mapping[str, Path]) -> dict[str, str]:
    return {str(k): sha256_file(Path(p)) for k, p in sorted(paths.items(), key=lambda kv: str(kv[0]))}


def load_record(path: Path) -> dict[str, str] | None:
    path = Path(path)
    if not path.exists():
        return None
    obj = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(obj, dict) and isinstance(obj.get("sha256", None), dict):
        sha = obj["sha256"]
        return _stable_map({str(k): str(v) for k, v in sha.items()})
    if isinstance(obj, dict) and all(isinstance(v, str) for v in obj.values()):
        # Legacy/simple format: {key: sha256, ...}
        return _stable_map({str(k): str(v) for k, v in obj.items()})
    raise ValueError(f"Invalid sha256 record format: {path}")


def compare_record(path: Path, paths: Mapping[str, Path]) -> tuple[bool, dict[str, str], dict[str, str] | None]:
    prev = load_record(path)
    cur = compute_sha256_map(paths)
    if prev is None:
        return False, cur, None
    return bool(_stable_map(prev) == _stable_map(cur)), cur, prev


def write_record(path: Path, paths: Mapping[str, Path], sha256_map: Mapping[str, str] | None = None) -> dict[str, str]:
    path = Path(path)
    sha = compute_sha256_map(paths) if sha256_map is None else _stable_map({str(k): str(v) for k, v in sha256_map.items()})
    payload = {
        "version": "inputs_parquet_sha256_v1",
        "created_unix": float(time.time()),
        "paths": {str(k): str(Path(p)) for k, p in sorted(paths.items(), key=lambda kv: str(kv[0]))},
        "sha256": dict(sha),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return dict(sha)


def mismatch_summary(cur: Mapping[str, str], prev: Mapping[str, str] | None) -> str:
    cur = _stable_map(cur)
    prev = {} if prev is None else _stable_map(prev)
    keys = sorted(set(cur.keys()) | set(prev.keys()))
    diffs: list[str] = []
    for k in keys:
        a = prev.get(k, "")
        b = cur.get(k, "")
        if a != b:
            diffs.append(f"{k}: {a[:10]} -> {b[:10]}")
    if not diffs:
        return "no_diff"
    return "; ".join(diffs)

