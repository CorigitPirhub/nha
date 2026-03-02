from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class SampleRef:
    path: Path
    difficulty: str
    scenario: str
    task_type: str
    category: str


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build hard+non-hard replay mixed dataset from existing NPZ files."
    )
    p.add_argument(
        "--hard-roots",
        type=str,
        default="data/structrank_hard_v1",
        help="Comma-separated roots. Hard samples are collected from train/val where difficulty=='hard'.",
    )
    p.add_argument(
        "--replay-roots",
        type=str,
        default="data/structrank_mix_v2,data/residual_fix_v3",
        help="Comma-separated roots. Non-hard samples are collected where difficulty!='hard'.",
    )
    p.add_argument(
        "--output-root",
        type=Path,
        default=Path("data/replay_hard_nonhard_v1"),
    )
    p.add_argument("--train-hard-count", type=int, default=180)
    p.add_argument("--val-hard-count", type=int, default=40)
    p.add_argument("--train-nonhard-count", type=int, default=100)
    p.add_argument("--val-nonhard-count", type=int, default=12)
    p.add_argument("--seed", type=int, default=43)
    return p.parse_args()


def _read_meta(path: Path) -> SampleRef | None:
    try:
        with np.load(path, allow_pickle=False) as z:
            difficulty = str(z["difficulty"]) if "difficulty" in z else "unknown"
            scenario = str(z["scenario"]) if "scenario" in z else "unknown"
            task_type = str(z["task_type"]) if "task_type" in z else "unknown"
            category = str(z["category"]) if "category" in z else "U"
        return SampleRef(path=path, difficulty=difficulty, scenario=scenario, task_type=task_type, category=category)
    except Exception:
        return None


def _collect(root: Path, split: str) -> list[SampleRef]:
    out: list[SampleRef] = []
    d = root / split
    if not d.exists():
        return out
    for p in sorted(d.glob("sample_*.npz")):
        row = _read_meta(p)
        if row is not None:
            out.append(row)
    return out


def _sample_refs(
    refs: list[SampleRef],
    count: int,
    rng: np.random.Generator,
    allow_replay: bool,
) -> tuple[list[SampleRef], int]:
    count = int(max(count, 0))
    if count == 0 or not refs:
        return [], 0
    n = len(refs)
    if count <= n:
        idx = rng.choice(n, size=count, replace=False)
        return [refs[int(i)] for i in idx], 0
    if not allow_replay:
        idx = rng.choice(n, size=n, replace=False)
        return [refs[int(i)] for i in idx], 0
    base_idx = rng.choice(n, size=n, replace=False)
    extra = count - n
    replay_idx = rng.choice(n, size=extra, replace=True)
    picked = [refs[int(i)] for i in base_idx] + [refs[int(i)] for i in replay_idx]
    return picked, int(extra)


def _copy_split(
    split: str,
    hard_refs: list[SampleRef],
    nonhard_refs: list[SampleRef],
    out_root: Path,
    rng: np.random.Generator,
) -> dict:
    dst = out_root / split
    dst.mkdir(parents=True, exist_ok=True)
    for p in dst.glob("sample_*.npz"):
        p.unlink()

    all_refs = list(hard_refs) + list(nonhard_refs)
    if all_refs:
        order = rng.permutation(len(all_refs))
        all_refs = [all_refs[int(i)] for i in order]

    hist_diff: dict[str, int] = {}
    hist_scenario: dict[str, int] = {}
    hist_task: dict[str, int] = {}
    hist_cat: dict[str, int] = {}
    for i, ref in enumerate(all_refs):
        out = dst / f"sample_{i:06d}.npz"
        shutil.copy2(ref.path, out)
        hist_diff[ref.difficulty] = hist_diff.get(ref.difficulty, 0) + 1
        hist_scenario[ref.scenario] = hist_scenario.get(ref.scenario, 0) + 1
        hist_task[ref.task_type] = hist_task.get(ref.task_type, 0) + 1
        hist_cat[ref.category] = hist_cat.get(ref.category, 0) + 1

    n = len(all_refs)
    n_hard = sum(1 for r in all_refs if r.difficulty.lower() == "hard")
    n_nonhard = n - n_hard
    return {
        "split": split,
        "num_samples": n,
        "hard_samples": n_hard,
        "nonhard_samples": n_nonhard,
        "nonhard_ratio": float(n_nonhard / max(n, 1)),
        "difficulty_histogram": hist_diff,
        "scenario_histogram": hist_scenario,
        "task_histogram": hist_task,
        "category_histogram": hist_cat,
    }


def main() -> None:
    args = _parse_args()
    rng = np.random.default_rng(int(args.seed))

    hard_roots = [Path(x.strip()) for x in str(args.hard_roots).split(",") if x.strip()]
    replay_roots = [Path(x.strip()) for x in str(args.replay_roots).split(",") if x.strip()]

    hard_train_pool: list[SampleRef] = []
    hard_val_pool: list[SampleRef] = []
    nonhard_pool_all: list[SampleRef] = []

    for r in hard_roots:
        hard_train_pool.extend([x for x in _collect(r, "train") if x.difficulty.lower() == "hard"])
        hard_val_pool.extend([x for x in _collect(r, "val") if x.difficulty.lower() == "hard"])

    for r in replay_roots:
        for s in ("train", "val"):
            nonhard_pool_all.extend([x for x in _collect(r, s) if x.difficulty.lower() != "hard"])

    if not hard_train_pool or not hard_val_pool:
        raise RuntimeError("Hard pool is empty; check --hard-roots.")
    if not nonhard_pool_all:
        raise RuntimeError("Non-hard replay pool is empty; check --replay-roots.")

    # Split non-hard pool into train/val source sets first, then replay as needed.
    n_nonhard = len(nonhard_pool_all)
    perm = rng.permutation(n_nonhard)
    nonhard_pool_all = [nonhard_pool_all[int(i)] for i in perm]
    # keep a small held-out subset for val source
    val_src_n = max(4, int(round(0.15 * n_nonhard)))
    val_src_n = min(val_src_n, max(n_nonhard - 1, 1))
    nonhard_val_pool = nonhard_pool_all[:val_src_n]
    nonhard_train_pool = nonhard_pool_all[val_src_n:]
    if not nonhard_train_pool:
        nonhard_train_pool = list(nonhard_pool_all)
    if not nonhard_val_pool:
        nonhard_val_pool = list(nonhard_pool_all)

    hard_train_pick, hard_train_replay = _sample_refs(
        refs=hard_train_pool,
        count=int(args.train_hard_count),
        rng=rng,
        allow_replay=False,
    )
    hard_val_pick, hard_val_replay = _sample_refs(
        refs=hard_val_pool,
        count=int(args.val_hard_count),
        rng=rng,
        allow_replay=False,
    )
    nonhard_train_pick, nonhard_train_replay = _sample_refs(
        refs=nonhard_train_pool,
        count=int(args.train_nonhard_count),
        rng=rng,
        allow_replay=True,
    )
    nonhard_val_pick, nonhard_val_replay = _sample_refs(
        refs=nonhard_val_pool,
        count=int(args.val_nonhard_count),
        rng=rng,
        allow_replay=True,
    )

    out_root = Path(args.output_root)
    out_root.mkdir(parents=True, exist_ok=True)

    train_meta = _copy_split(
        split="train",
        hard_refs=hard_train_pick,
        nonhard_refs=nonhard_train_pick,
        out_root=out_root,
        rng=rng,
    )
    val_meta = _copy_split(
        split="val",
        hard_refs=hard_val_pick,
        nonhard_refs=nonhard_val_pick,
        out_root=out_root,
        rng=rng,
    )
    # Keep test empty for training-only pipeline compatibility.
    test_dir = out_root / "test"
    test_dir.mkdir(parents=True, exist_ok=True)
    for p in test_dir.glob("sample_*.npz"):
        p.unlink()

    meta = {
        "seed": int(args.seed),
        "name": "replay_hard_nonhard_mix",
        "hard_roots": [str(p) for p in hard_roots],
        "replay_roots": [str(p) for p in replay_roots],
        "selected_counts": {
            "train_hard_count": int(args.train_hard_count),
            "train_nonhard_count": int(args.train_nonhard_count),
            "val_hard_count": int(args.val_hard_count),
            "val_nonhard_count": int(args.val_nonhard_count),
        },
        "replay_counts": {
            "train_hard_replay": int(hard_train_replay),
            "train_nonhard_replay": int(nonhard_train_replay),
            "val_hard_replay": int(hard_val_replay),
            "val_nonhard_replay": int(nonhard_val_replay),
        },
        "splits": {
            "train": train_meta,
            "val": val_meta,
            "test": {"split": "test", "num_samples": 0},
        },
    }
    (out_root / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[done] wrote dataset at: {out_root}")
    print(json.dumps(meta["splits"], indent=2, ensure_ascii=False))
    print(json.dumps(meta["replay_counts"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
