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
    p = argparse.ArgumentParser(description="Build Phase-9 public mixed benchmark dataset.")
    p.add_argument("--benchmark-root", type=Path, default=Path("data/benchmark"))
    p.add_argument("--out-root", type=Path, default=Path("data/router_phase9_public_v1"))
    p.add_argument("--seed", type=int, default=20260302)
    p.add_argument("--test-mp", type=int, default=2300)
    p.add_argument("--test-csm", type=int, default=900)
    p.add_argument("--test-parasol", type=int, default=18)
    p.add_argument("--calib-mp", type=int, default=1500)
    p.add_argument("--calib-csm", type=int, default=300)
    p.add_argument(
        "--ood-map-ids",
        type=str,
        default="mp_mazes,mp_bugtrap_forest,packed_018,packed_019",
        help="Comma-separated map_id list marked as OOD family.",
    )
    return p.parse_args()


def _normalize_difficulty(raw: str, source_dataset: str) -> str:
    x = str(raw).strip().lower()
    if x in {"simple", "easy"}:
        return "easy"
    if x in {"medium", "normal"}:
        return "medium"
    if x in {"hard", "difficult"}:
        return "hard"
    # Keep parasol as hard by default.
    return "hard" if source_dataset == "parasol" else "medium"


def _sha256_lines(lines: list[str]) -> str:
    h = hashlib.sha256()
    for ln in lines:
        h.update(ln.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def _load_case(path: Path, split_hint: str) -> CaseMeta:
    with np.load(path, allow_pickle=False) as z:
        source_dataset = str(z["source_dataset"]) if "source_dataset" in z else path.parts[-3]
        scenario = str(z["scenario"]) if "scenario" in z else "unknown"
        category = str(z["category"]) if "category" in z else "unknown"
        map_id = str(z["map_id"]) if "map_id" in z else path.stem
        difficulty_raw = str(z["difficulty"]) if "difficulty" in z else "hard"
    source_dataset = source_dataset.lower()
    return CaseMeta(
        source_path=path.resolve(),
        source_dataset=source_dataset,
        scenario=scenario,
        category=category,
        map_id=map_id,
        difficulty_raw=difficulty_raw,
        difficulty=_normalize_difficulty(difficulty_raw, source_dataset=source_dataset),
        split_hint=split_hint,
    )


def _collect_all(root: Path) -> dict[str, list[CaseMeta]]:
    out: dict[str, list[CaseMeta]] = {"mp": [], "csm": [], "parasol": []}
    for ds in ("mp", "csm"):
        for split in ("train", "test"):
            for p in sorted((root / ds / split).glob("sample_*.npz")):
                out[ds].append(_load_case(p, split_hint=f"{ds}:{split}"))
    for split in ("train", "test"):
        for p in sorted((root / "parasol_narrow" / split).glob("sample_*.npz")):
            out["parasol"].append(_load_case(p, split_hint=f"parasol:{split}"))
    return out


def _parse_ood_map_ids(text: str) -> set[str]:
    out: set[str] = set()
    for tok in str(text).split(","):
        tok = tok.strip()
        if tok:
            out.add(tok)
    return out


def _ood_name(case: CaseMeta) -> str:
    return f"{case.source_dataset}::{case.map_id}"


def _is_ood(case: CaseMeta, ood_map_ids: set[str]) -> bool:
    if case.source_dataset == "parasol":
        return True
    return case.map_id in ood_map_ids


def _write_split(cases: list[CaseMeta], split: str, out_root: Path, ood_map_ids: set[str]) -> dict:
    split_dir = out_root / split
    split_dir.mkdir(parents=True, exist_ok=True)
    index_csv = out_root / f"{split}_index.csv"

    rows: list[dict] = []
    src_lines: list[str] = []
    for i, c in enumerate(cases):
        dst_name = f"sample_{i:06d}.npz"
        dst = split_dir / dst_name
        if dst.exists() or dst.is_symlink():
            dst.unlink()
        dst.symlink_to(c.source_path)

        ood = int(_is_ood(c, ood_map_ids=ood_map_ids))
        rows.append(
            {
                "split": split,
                "sample_name": dst_name,
                "source_path": str(c.source_path),
                "source_dataset": c.source_dataset,
                "scenario": c.scenario,
                "category": c.category,
                "map_id": c.map_id,
                "difficulty_raw": c.difficulty_raw,
                "difficulty": c.difficulty,
                "ood_family": int(ood),
                "ood_family_name": _ood_name(c) if ood else "",
                "split_hint": c.split_hint,
            }
        )
        src_lines.append(str(c.source_path))

    with index_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    by_src: dict[str, int] = {}
    by_diff: dict[str, int] = {}
    by_scenario: dict[str, int] = {}
    ood_cnt = 0
    ood_fams: set[str] = set()
    for r in rows:
        by_src[r["source_dataset"]] = by_src.get(r["source_dataset"], 0) + 1
        by_diff[r["difficulty"]] = by_diff.get(r["difficulty"], 0) + 1
        by_scenario[r["scenario"]] = by_scenario.get(r["scenario"], 0) + 1
        if int(r["ood_family"]) == 1:
            ood_cnt += 1
            if r["ood_family_name"]:
                ood_fams.add(str(r["ood_family_name"]))

    return {
        "num_cases": int(len(rows)),
        "source_counts": by_src,
        "difficulty_counts": by_diff,
        "scenario_counts": by_scenario,
        "ood_family_cases": int(ood_cnt),
        "ood_family_ratio": float(ood_cnt / max(len(rows), 1)),
        "ood_family_unique": int(len(ood_fams)),
        "source_sha256": _sha256_lines(src_lines),
        "index_csv": str(index_csv),
    }


def main() -> None:
    args = parse_args()
    rng = np.random.default_rng(int(args.seed))

    out_root = args.out_root
    out_root.mkdir(parents=True, exist_ok=True)

    all_cases = _collect_all(args.benchmark_root)
    for ds in all_cases:
        arr = all_cases[ds]
        idx = np.arange(len(arr), dtype=np.int64)
        rng.shuffle(idx)
        all_cases[ds] = [arr[i] for i in idx.tolist()]

    n_test_mp = int(args.test_mp)
    n_test_csm = int(args.test_csm)
    n_test_parasol = int(args.test_parasol)
    n_calib_mp = int(args.calib_mp)
    n_calib_csm = int(args.calib_csm)

    if len(all_cases["mp"]) < (n_test_mp + n_calib_mp):
        raise RuntimeError(f"Insufficient MP cases: have {len(all_cases['mp'])}, need {n_test_mp + n_calib_mp}")
    if len(all_cases["csm"]) < (n_test_csm + n_calib_csm):
        raise RuntimeError(f"Insufficient CSM cases: have {len(all_cases['csm'])}, need {n_test_csm + n_calib_csm}")
    if len(all_cases["parasol"]) < n_test_parasol:
        raise RuntimeError(f"Insufficient Parasol cases: have {len(all_cases['parasol'])}, need {n_test_parasol}")

    test_cases = all_cases["mp"][:n_test_mp] + all_cases["csm"][:n_test_csm] + all_cases["parasol"][:n_test_parasol]
    mp_remain = all_cases["mp"][n_test_mp:]
    csm_remain = all_cases["csm"][n_test_csm:]
    parasol_remain = all_cases["parasol"][n_test_parasol:]

    calib_cases = mp_remain[:n_calib_mp] + csm_remain[:n_calib_csm]
    train_cases = mp_remain[n_calib_mp:] + csm_remain[n_calib_csm:] + parasol_remain

    def _sort_key(c: CaseMeta):
        return (c.source_dataset, c.scenario, c.map_id, c.source_path.name)

    test_cases = sorted(test_cases, key=_sort_key)
    calib_cases = sorted(calib_cases, key=_sort_key)
    train_cases = sorted(train_cases, key=_sort_key)

    for sp in ("train", "calib", "test"):
        d = out_root / sp
        d.mkdir(parents=True, exist_ok=True)
        for p in d.glob("sample_*.npz"):
            p.unlink()

    ood_map_ids = _parse_ood_map_ids(args.ood_map_ids)
    train_stat = _write_split(train_cases, "train", out_root, ood_map_ids=ood_map_ids)
    calib_stat = _write_split(calib_cases, "calib", out_root, ood_map_ids=ood_map_ids)
    test_stat = _write_split(test_cases, "test", out_root, ood_map_ids=ood_map_ids)

    manifest = {
        "version": "router_phase9_public_v1",
        "seed": int(args.seed),
        "source_root": str(args.benchmark_root.resolve()),
        "allocation": {
            "test_mp": n_test_mp,
            "test_csm": n_test_csm,
            "test_parasol": n_test_parasol,
            "calib_mp": n_calib_mp,
            "calib_csm": n_calib_csm,
            "ood_map_ids": sorted(ood_map_ids),
        },
        "splits": {
            "train": train_stat,
            "calib": calib_stat,
            "test": test_stat,
        },
        "phase9_dataset_gate_check": {
            "test_cases_ge_3000": bool(int(test_stat["num_cases"]) >= 3000),
            "public_benchmarks_ge_3": bool(len(test_stat["source_counts"]) >= 3),
            "ood_families_ge_2": bool(int(test_stat["ood_family_unique"]) >= 2),
        },
    }
    manifest_path = out_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"[phase9-dataset] manifest={manifest_path}")
    print(f"[phase9-dataset] train={train_stat['num_cases']} calib={calib_stat['num_cases']} test={test_stat['num_cases']}")
    print(f"[phase9-dataset] test source={test_stat['source_counts']}")
    print(
        f"[phase9-dataset] test ood unique={test_stat['ood_family_unique']} "
        f"ratio={test_stat['ood_family_ratio']:.4f}"
    )


if __name__ == "__main__":
    main()

