from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DEFAULT_CONFIG
from env.dataset_builder import describe_split, generate_dataset_split
from utils.common import set_seed


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate training/validation/test datasets")
    p.add_argument("--output", type=Path, default=Path("data"))
    p.add_argument("--train", type=int, default=DEFAULT_CONFIG.dataset.train_size)
    p.add_argument("--val", type=int, default=DEFAULT_CONFIG.dataset.val_size)
    p.add_argument("--test", type=int, default=DEFAULT_CONFIG.dataset.test_size)
    p.add_argument("--seed", type=int, default=DEFAULT_CONFIG.seed)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = DEFAULT_CONFIG
    set_seed(args.seed)

    train_counts = generate_dataset_split(
        args.output / "train",
        args.train,
        cfg.map,
        cfg.dataset,
        seed=args.seed + 11,
    )
    val_counts = generate_dataset_split(
        args.output / "val",
        args.val,
        cfg.map,
        cfg.dataset,
        seed=args.seed + 22,
    )
    test_counts = generate_dataset_split(
        args.output / "test",
        args.test,
        cfg.map,
        cfg.dataset,
        seed=args.seed + 33,
    )

    print(describe_split("train", train_counts))
    print(describe_split("val", val_counts))
    print(describe_split("test", test_counts))


if __name__ == "__main__":
    main()
