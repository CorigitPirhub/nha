from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class CaseMeta:
    source_path: Path
    source_dataset: str
    scenario: str
    category: str
    map_id: str
    difficulty_raw: str
    difficulty: str
    split_hint: str


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build mixed-difficulty dataset for router evaluation.")
    p.add_argument("--benchmark-root", type=Path, default=Path("data/benchmark"))
    p.add_argument("--out-root", type=Path, default=Path("data/router_mixed_v1"))
    p.add_argument("--seed", type=int, default=20260302)
    p.add_argument("--test-size", type=int, default=900)
    p.add_argument("--test-per-difficulty", type=int, default=300)
    p.add_argument("--calib-per-difficulty", type=int, default=500)
    p.add_argument("--test-csm-easy", type=int, default=90)
    p.add_argument("--test-csm-medium", type=int, default=150)
    p.add_argument("--test-csm-hard", type=int, default=60)
    return p.parse_args()


def _normalize_difficulty(raw: str) -> str:
    x = str(raw).strip().lower()
    if x in {"simple", "easy"}:
        return "easy"
    if x in {"medium", "normal"}:
        return "medium"
    if x in {"hard", "difficult"}:
        return "hard"
    return "hard"


def _load_case_meta(path: Path, split_hint: str) -> CaseMeta:
    with np.load(path, allow_pickle=False) as z:
        source_dataset = str(z["source_dataset"]) if "source_dataset" in z else path.parts[-3]
        scenario = str(z["scenario"]) if "scenario" in z else "unknown"
        category = str(z["category"]) if "category" in z else "unknown"
        map_id = str(z["map_id"]) if "map_id" in z else path.stem
        difficulty_raw = str(z["difficulty"]) if "difficulty" in z else "hard"
    return CaseMeta(
        source_path=path.resolve(),
        source_dataset=source_dataset.lower(),
        scenario=scenario,
        category=category,
        map_id=map_id,
        difficulty_raw=difficulty_raw,
        difficulty=_normalize_difficulty(difficulty_raw),
        split_hint=split_hint,
    )


def _collect_cases(benchmark_root: Path) -> list[CaseMeta]:
    out: list[CaseMeta] = []
    for ds in ["mp", "csm"]:
        for split in ["train", "test"]:
            for p in sorted((benchmark_root / ds / split).glob("sample_*.npz")):
                out.append(_load_case_meta(path=p, split_hint=f"{ds}:{split}"))
    if not out:
        raise FileNotFoundError(f"No benchmark files found under {benchmark_root}")
    return out


def _sha256_lines(lines: list[str]) -> str:
    h = hashlib.sha256()
    for ln in lines:
        h.update(ln.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def _write_split(
    cases: list[CaseMeta],
    split_name: str,
    out_root: Path,
) -> dict:
    split_dir = out_root / split_name
    split_dir.mkdir(parents=True, exist_ok=True)

    index_path = out_root / f"{split_name}_index.csv"
    rows: list[dict] = []
    source_lines: list[str] = []
    for i, c in enumerate(cases):
        rel_name = f"sample_{i:06d}.npz"
        dst = split_dir / rel_name
        if dst.exists() or dst.is_symlink():
            dst.unlink()
        dst.symlink_to(c.source_path)

        ood_family = bool(c.source_dataset == "csm")
        row = {
            "split": split_name,
            "sample_name": rel_name,
            "source_path": str(c.source_path),
            "source_dataset": c.source_dataset,
            "scenario": c.scenario,
            "category": c.category,
            "map_id": c.map_id,
            "difficulty_raw": c.difficulty_raw,
            "difficulty": c.difficulty,
            "ood_family": int(ood_family),
            "split_hint": c.split_hint,
        }
        rows.append(row)
        source_lines.append(str(c.source_path))

    with index_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    by_diff: dict[str, int] = {}
    by_src: dict[str, int] = {}
    by_scenario: dict[str, int] = {}
    ood = 0
    for r in rows:
        by_diff[r["difficulty"]] = by_diff.get(r["difficulty"], 0) + 1
        by_src[r["source_dataset"]] = by_src.get(r["source_dataset"], 0) + 1
        by_scenario[r["scenario"]] = by_scenario.get(r["scenario"], 0) + 1
        ood += int(r["ood_family"])
    out = {
        "num_cases": len(rows),
        "difficulty_counts": by_diff,
        "source_counts": by_src,
        "scenario_counts": by_scenario,
        "ood_family_cases": ood,
        "ood_family_ratio": float(ood / max(len(rows), 1)),
        "source_sha256": _sha256_lines(source_lines),
        "index_csv": str(index_path),
    }
    return out


def main() -> None:
    args = parse_args()
    rng = np.random.default_rng(args.seed)

    out_root = args.out_root
    out_root.mkdir(parents=True, exist_ok=True)

    all_cases = _collect_cases(args.benchmark_root)
    pool: dict[tuple[str, str], list[CaseMeta]] = {}
    for c in all_cases:
        key = (c.difficulty, c.source_dataset)
        pool.setdefault(key, []).append(c)
    for k in pool:
        arr = pool[k]
        idx = np.arange(len(arr), dtype=np.int64)
        rng.shuffle(idx)
        pool[k] = [arr[i] for i in idx.tolist()]

    test_csm_plan = {
        "easy": int(args.test_csm_easy),
        "medium": int(args.test_csm_medium),
        "hard": int(args.test_csm_hard),
    }
    test_per_diff = int(args.test_per_difficulty)
    if int(sum(test_csm_plan.values())) <= 0:
        raise ValueError("Invalid csm test allocation.")
    if int(test_per_diff) <= 0:
        raise ValueError("test_per_difficulty must be > 0.")

    test_cases: list[CaseMeta] = []
    for d in ["easy", "medium", "hard"]:
        csm_n = int(test_csm_plan[d])
        mp_n = int(test_per_diff - csm_n)
        if csm_n < 0 or mp_n < 0:
            raise ValueError(f"Invalid test allocation for difficulty {d}: csm={csm_n}, mp={mp_n}")
        if len(pool.get((d, "csm"), [])) < csm_n:
            raise RuntimeError(f"Insufficient csm cases for {d}: need {csm_n}, have {len(pool.get((d, 'csm'), []))}")
        if len(pool.get((d, "mp"), [])) < mp_n:
            raise RuntimeError(f"Insufficient mp cases for {d}: need {mp_n}, have {len(pool.get((d, 'mp'), []))}")
        test_cases.extend(pool[(d, "csm")][:csm_n])
        pool[(d, "csm")] = pool[(d, "csm")][csm_n:]
        test_cases.extend(pool[(d, "mp")][:mp_n])
        pool[(d, "mp")] = pool[(d, "mp")][mp_n:]

    if len(test_cases) != int(args.test_size):
        raise RuntimeError(f"test size mismatch: got {len(test_cases)}, expected {args.test_size}")

    calib_cases: list[CaseMeta] = []
    calib_per_diff = int(args.calib_per_difficulty)
    for d in ["easy", "medium", "hard"]:
        merged = pool.get((d, "mp"), []) + pool.get((d, "csm"), [])
        if len(merged) < calib_per_diff:
            raise RuntimeError(f"Insufficient remaining cases for calib {d}: need {calib_per_diff}, have {len(merged)}")
        idx = np.arange(len(merged), dtype=np.int64)
        rng.shuffle(idx)
        calib_sel = [merged[i] for i in idx[:calib_per_diff].tolist()]
        calib_cases.extend(calib_sel)
        sel_set = set(calib_sel)
        pool[(d, "mp")] = [x for x in pool.get((d, "mp"), []) if x not in sel_set]
        pool[(d, "csm")] = [x for x in pool.get((d, "csm"), []) if x not in sel_set]

    train_cases: list[CaseMeta] = []
    for d in ["easy", "medium", "hard"]:
        train_cases.extend(pool.get((d, "mp"), []))
        train_cases.extend(pool.get((d, "csm"), []))

    # Deterministic order in splits.
    def sort_key(c: CaseMeta):
        return (c.source_dataset, c.scenario, c.map_id, c.source_path.name)

    test_cases = sorted(test_cases, key=sort_key)
    calib_cases = sorted(calib_cases, key=sort_key)
    train_cases = sorted(train_cases, key=sort_key)

    for split in ["train", "calib", "test"]:
        split_dir = out_root / split
        split_dir.mkdir(parents=True, exist_ok=True)
        for p in split_dir.glob("sample_*.npz"):
            p.unlink()

    train_stat = _write_split(train_cases, "train", out_root)
    calib_stat = _write_split(calib_cases, "calib", out_root)
    test_stat = _write_split(test_cases, "test", out_root)

    # Hard gate checks from TASK.md Phase 1.
    if test_stat["num_cases"] < 900:
        raise RuntimeError(f"test size gate failed: {test_stat['num_cases']} < 900")
    for d in ["easy", "medium", "hard"]:
        n = int(test_stat["difficulty_counts"].get(d, 0))
        if n < 250:
            raise RuntimeError(f"test difficulty gate failed: {d}={n} < 250")
    if float(test_stat["ood_family_ratio"]) < 0.30:
        raise RuntimeError(f"OOD ratio gate failed: {test_stat['ood_family_ratio']:.4f} < 0.30")

    manifest = {
        "version": "router_mixed_v1",
        "seed": int(args.seed),
        "source_root": str(args.benchmark_root.resolve()),
        "splits": {
            "train": train_stat,
            "calib": calib_stat,
            "test": test_stat,
        },
        "allocation": {
            "test_size": int(args.test_size),
            "test_per_difficulty": int(args.test_per_difficulty),
            "calib_per_difficulty": int(args.calib_per_difficulty),
            "test_csm": test_csm_plan,
        },
        "phase1_gate_check": {
            "test_ge_900": bool(test_stat["num_cases"] >= 900),
            "each_difficulty_ge_250": {
                d: bool(int(test_stat["difficulty_counts"].get(d, 0)) >= 250)
                for d in ["easy", "medium", "hard"]
            },
            "ood_ratio_ge_30pct": bool(float(test_stat["ood_family_ratio"]) >= 0.30),
        },
    }
    manifest_path = out_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"[router_mixed] saved: {manifest_path}")
    print(f"[router_mixed] split sizes: train={train_stat['num_cases']}, calib={calib_stat['num_cases']}, test={test_stat['num_cases']}")
    print(f"[router_mixed] test difficulty: {test_stat['difficulty_counts']}")
    print(f"[router_mixed] test source: {test_stat['source_counts']}, ood_ratio={test_stat['ood_family_ratio']:.4f}")


if __name__ == "__main__":
    main()
