from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class TreeNode:
    feature_index: int
    threshold: float
    prob: float
    left: 'TreeNode | None' = None
    right: 'TreeNode | None' = None

    @property
    def is_leaf(self) -> bool:
        return self.left is None or self.right is None or int(self.feature_index) < 0


@dataclass(frozen=True)
class SupportBand:
    low: np.ndarray
    high: np.ndarray
    prototype: np.ndarray
    similarity_floor: float
    min_progress: float
    counts: int


def _gini(y: np.ndarray) -> float:
    if y.size <= 0:
        return 0.0
    p = float(np.mean(y))
    return 1.0 - p * p - (1.0 - p) * (1.0 - p)


def _best_split(x: np.ndarray, y: np.ndarray, min_leaf: int = 2) -> tuple[int, float, float] | None:
    n, d = x.shape
    if n < 2 * int(min_leaf):
        return None
    parent = _gini(y)
    best: tuple[int, float, float] | None = None
    for feat in range(d):
        values = np.unique(np.asarray(x[:, feat], dtype=np.float32))
        if values.size < 2:
            continue
        thresholds = (values[:-1] + values[1:]) * 0.5
        for thr in thresholds:
            left = x[:, feat] <= float(thr)
            right = ~left
            if int(np.sum(left)) < int(min_leaf) or int(np.sum(right)) < int(min_leaf):
                continue
            gain = parent - (
                float(np.sum(left)) / float(n) * _gini(y[left])
                + float(np.sum(right)) / float(n) * _gini(y[right])
            )
            if best is None or gain > best[2] + 1e-9:
                best = (int(feat), float(thr), float(gain))
    return best


def fit_tree(x: np.ndarray, y: np.ndarray, max_depth: int, depth: int = 0) -> TreeNode:
    prob = float(np.mean(y)) if y.size else 0.0
    if depth >= int(max_depth) or y.size <= 2 or np.all(y == y[0]):
        return TreeNode(feature_index=-1, threshold=0.0, prob=prob)
    split = _best_split(x, y)
    if split is None or split[2] <= 1e-9:
        return TreeNode(feature_index=-1, threshold=0.0, prob=prob)
    feat, thr, _ = split
    left_mask = x[:, feat] <= float(thr)
    right_mask = ~left_mask
    left = fit_tree(x[left_mask], y[left_mask], max_depth=max_depth, depth=depth + 1)
    right = fit_tree(x[right_mask], y[right_mask], max_depth=max_depth, depth=depth + 1)
    return TreeNode(feature_index=int(feat), threshold=float(thr), prob=prob, left=left, right=right)


def predict_tree(tree: TreeNode, x: np.ndarray) -> float:
    cur = tree
    feat = np.asarray(x, dtype=np.float32)
    while cur is not None and not cur.is_leaf:
        cur = cur.left if float(feat[cur.feature_index]) <= float(cur.threshold) else cur.right
    return float(cur.prob if cur is not None else 0.0)


def tree_to_dict(tree: TreeNode, names: tuple[str, ...]) -> dict[str, Any]:
    out: dict[str, Any] = {
        'feature_index': int(tree.feature_index),
        'feature_name': names[tree.feature_index] if int(tree.feature_index) >= 0 else 'leaf',
        'threshold': float(tree.threshold),
        'prob': float(tree.prob),
    }
    if tree.left is not None:
        out['left'] = tree_to_dict(tree.left, names)
    if tree.right is not None:
        out['right'] = tree_to_dict(tree.right, names)
    return out


def fit_support_band(rows: list[np.ndarray], progresses: list[float], *, low_q: float, high_q: float, sim_q: float) -> SupportBand | None:
    if not rows:
        return None
    x = np.stack([np.asarray(r, dtype=np.float32) for r in rows], axis=0)
    mean = x.mean(axis=0, keepdims=True).astype(np.float32)
    std = x.std(axis=0, keepdims=True).astype(np.float32)
    std[std < 1e-6] = 1.0
    z = ((x - mean) / std).astype(np.float32)
    proto = np.mean(z, axis=0).astype(np.float32)
    n = float(np.linalg.norm(proto))
    if n > 1e-6:
        proto = proto / n
    sims = []
    for row in z:
        r = row.astype(np.float32)
        rn = float(np.linalg.norm(r))
        if rn > 1e-6:
            r = r / rn
        sims.append(float(np.dot(r, proto)))
    low = np.quantile(x, float(low_q), axis=0).astype(np.float32)
    high = np.quantile(x, float(high_q), axis=0).astype(np.float32)
    return SupportBand(
        low=low,
        high=high,
        prototype=np.concatenate([mean[0], std[0], proto], axis=0).astype(np.float32),
        similarity_floor=float(np.quantile(np.asarray(sims, dtype=np.float32), float(sim_q))),
        min_progress=float(np.quantile(np.asarray(progresses, dtype=np.float32), 0.2)) if len(progresses) else 0.0,
        counts=int(len(rows)),
    )


def support_match(band: SupportBand | None, feat: np.ndarray, progress: float, *, slack: float) -> tuple[bool, float]:
    if band is None:
        return False, 0.0
    feat = np.asarray(feat, dtype=np.float32)
    dim = feat.shape[0]
    low = np.asarray(band.low, dtype=np.float32) - float(slack)
    high = np.asarray(band.high, dtype=np.float32) + float(slack)
    within = np.all((feat >= low) & (feat <= high))
    mean = np.asarray(band.prototype[:dim], dtype=np.float32)
    std = np.asarray(band.prototype[dim : 2 * dim], dtype=np.float32)
    proto = np.asarray(band.prototype[2 * dim :], dtype=np.float32)
    z = (feat - mean) / std
    zn = float(np.linalg.norm(z))
    if zn > 1e-6:
        z = z / zn
    sim = float(np.dot(z.astype(np.float32), proto.astype(np.float32)))
    good = bool(within and sim >= float(band.similarity_floor) and float(progress) >= float(band.min_progress))
    return good, float(sim)


__all__ = [
    'SupportBand',
    'TreeNode',
    'fit_support_band',
    'fit_tree',
    'predict_tree',
    'support_match',
    'tree_to_dict',
]
