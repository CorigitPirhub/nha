from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.router_policy_v1 import RouterPolicyV1, read_json, sha256_file


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate router policy artifact (v1).")
    p.add_argument("--artifact-dir", type=Path, default=Path("artifacts/router_policy_v1"))
    p.add_argument("--check-model-sha", action="store_true", default=True)
    p.add_argument("--check-policy-sha", action="store_true", default=True)
    return p.parse_args()


def _read_policy_sha(path: Path) -> str:
    txt = path.read_text(encoding="utf-8").strip()
    if not txt:
        raise ValueError(f"Empty sha file: {path}")
    # Format: "<sha>  policy.json"
    sha = txt.split()[0].strip()
    if len(sha) != 64:
        raise ValueError(f"Invalid sha256 in {path}: {sha!r}")
    return sha


def main() -> None:
    args = parse_args()
    ad = Path(args.artifact_dir)
    policy_json = ad / "policy.json"
    if not policy_json.exists():
        raise FileNotFoundError(policy_json)

    # Basic schema load.
    obj = read_json(policy_json)
    if str(obj.get("version", "")) != "router_policy_v1":
        raise ValueError(f"Unsupported policy.json version: {obj.get('version')!r}")

    # Hash checks.
    sha_file = ad / "POLICY.sha256"
    if bool(args.check_policy_sha):
        if not sha_file.exists():
            raise FileNotFoundError(sha_file)
        want = _read_policy_sha(sha_file)
        got = sha256_file(policy_json)
        if got != want:
            raise RuntimeError(f"policy.json sha mismatch: want={want}, got={got}")

    if bool(args.check_model_sha):
        models = obj.get("models", {})
        for k in ("conformal_violation_clf", "cost_regressor", "probe_gain_regressor"):
            rec = models.get(k, {})
            rel = rec.get("joblib", "")
            want = str(rec.get("sha256", ""))
            if not rel or not want:
                raise ValueError(f"Missing model entry fields for {k}")
            model_path = ad / str(rel)
            if not model_path.exists():
                raise FileNotFoundError(model_path)
            got = sha256_file(model_path)
            if got != want:
                raise RuntimeError(f"{k} sha mismatch: want={want}, got={got}")

    # Loadable policy object.
    policy = RouterPolicyV1.load(ad)
    _ = policy.cfg  # access to ensure initialization.

    print(f"[validate_policy_v1] OK: {policy_json}")
    if sha_file.exists():
        print(f"[validate_policy_v1] sha256(policy.json)={sha256_file(policy_json)}")


if __name__ == "__main__":
    main()

