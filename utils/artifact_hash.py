from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    path = Path(path)
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(int(chunk_size))
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def sha256_paths(paths: dict[str, Path]) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, p in paths.items():
        out[str(k)] = sha256_file(Path(p))
    return out

