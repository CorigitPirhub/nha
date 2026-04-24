from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from rs_macro_rescue.stack.accepted import accepted_cx3d_nonholonomic, accepted_cx3d_standard
from rs_macro_rescue.stack.nonholonomic import run_hybrid_with_policy


@dataclass(frozen=True)
class SignatureSpec:
    clearance_bins: tuple[float, ...] = (0.35, 0.7, 1.2, 2.0)
    dist_bins: tuple[float, ...] = (2.0, 5.0, 10.0, 20.0)
    heading_bins: tuple[float, ...] = (-0.5, 0.0, 0.5, 0.85)
    trap_bins: tuple[float, ...] = (0.2, 0.4, 0.6, 0.8)
    corridor_bins: tuple[float, ...] = (0.2, 0.4, 0.6, 0.8)
    yaw_bins: int = 8


@dataclass(frozen=True)
class BucketSpec:
    stride_cells: int = 2
    yaw_stride: int = 2


@dataclass(frozen=True)
class BucketFeatures:
    key: tuple[int, int, int]
    trap: float
    corridor: float
    clearance: float


class EpisodeBucketEncoder:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], bucket_spec: BucketSpec) -> None:
        self.case = case
        self.bundle = augmented_bundle(bundle)
        self.bucket_spec = bucket_spec
        self.resolution = float(case['resolution'])
        self.inv_resolution = 1.0 / max(self.resolution, 1e-6)
        self.esdf = np.maximum(np.asarray(case['esdf'], dtype=np.float32), 0.0)
        self.trap = np.asarray(self.bundle['_cx14_trap'], dtype=np.float32)
        self.corridor = np.asarray(self.bundle['_cx14_corridor_score'], dtype=np.float32)
        self.height = int(self.esdf.shape[0])
        self.width = int(self.esdf.shape[1])
        self.yaw_bins = 8
        self.cache: dict[tuple[int, int, int], BucketFeatures] = {}

    def _bucket_key(self, states: np.ndarray) -> list[tuple[int, int, int]]:
        xy = np.asarray(states[:, :2], dtype=np.float32)
        yaw = np.asarray(states[:, 2], dtype=np.float32)
        gx = np.clip(np.floor(xy[:, 0] * self.inv_resolution).astype(np.int32), 0, self.width - 1)
        gy = np.clip(np.floor(xy[:, 1] * self.inv_resolution).astype(np.int32), 0, self.height - 1)
        yaw_bin = np.floor(((yaw + np.pi) / (2.0 * np.pi)) * float(self.yaw_bins)).astype(np.int32) % int(self.yaw_bins)
        stride = max(int(self.bucket_spec.stride_cells), 1)
        yaw_stride = max(int(self.bucket_spec.yaw_stride), 1)
        return [
            (int(gx_i // stride), int(gy_i // stride), int(yaw_i // yaw_stride))
            for gx_i, gy_i, yaw_i in zip(gx, gy, yaw_bin)
        ]

    def _materialize(self, key: tuple[int, int, int]) -> BucketFeatures:
        stride = max(int(self.bucket_spec.stride_cells), 1)
        yaw_stride = max(int(self.bucket_spec.yaw_stride), 1)
        bx, by, byaw = key
        gx = int(np.clip(bx * stride + (stride // 2), 0, self.width - 1))
        gy = int(np.clip(by * stride + (stride // 2), 0, self.height - 1))
        trap = float(self.trap[gy, gx])
        corridor = float(self.corridor[gy, gx])
        clearance = float(self.esdf[gy, gx])
        feat = BucketFeatures(
            key=(int(bx), int(by), int(byaw * yaw_stride)),
            trap=trap,
            corridor=corridor,
            clearance=clearance,
        )
        self.cache[key] = feat
        return feat

    def features(self, state: tuple[float, float, float]) -> BucketFeatures:
        states = np.asarray([state], dtype=np.float32)
        return self.features_many(states)[0]

    def features_many(self, states: np.ndarray | list[tuple[float, float, float]]) -> list[BucketFeatures]:
        states_arr = np.asarray(states, dtype=np.float32).reshape(-1, 3)
        keys = self._bucket_key(states_arr)
        out: list[BucketFeatures] = []
        for key in keys:
            feat = self.cache.get(key)
            if feat is None:
                feat = self._materialize(key)
            out.append(feat)
        return out


def normalize01(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr, dtype=np.float32)
    lo = float(np.min(arr))
    hi = float(np.max(arr))
    if hi <= lo + 1e-6:
        return np.zeros_like(arr, dtype=np.float32)
    return ((arr - lo) / (hi - lo)).astype(np.float32)


def trap_score_map(bundle: dict[str, Any]) -> np.ndarray:
    barrier = np.asarray(bundle['barrier'], dtype=np.float32)
    focus = np.asarray(bundle['focus'], dtype=np.float32)
    corridor = np.asarray(bundle['corridor'], dtype=np.float32)
    risk = np.asarray(bundle.get('risk', np.zeros_like(barrier)), dtype=np.float32)
    score = 0.40 * barrier + 0.25 * focus + 0.20 * (1.0 - corridor) + 0.15 * risk
    return normalize01(score)


def corridor_score_map(bundle: dict[str, Any]) -> np.ndarray:
    barrier = np.asarray(bundle['barrier'], dtype=np.float32)
    focus = np.asarray(bundle['focus'], dtype=np.float32)
    corridor = np.asarray(bundle['corridor'], dtype=np.float32)
    score = 0.55 * corridor + 0.25 * focus + 0.20 * (1.0 - barrier)
    return normalize01(score)


def augmented_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    if '_cx14_trap' in bundle and '_cx14_corridor_score' in bundle:
        return bundle
    out = dict(bundle)
    out['_cx14_trap'] = trap_score_map(bundle)
    out['_cx14_corridor_score'] = corridor_score_map(bundle)
    return out


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg) -> tuple[dict[str, Any], np.ndarray]:
    bundle, field = accepted_cx3d_nonholonomic(case, predictor, cfg)
    return augmented_bundle(bundle), np.asarray(field, dtype=np.float32)


def build_standard_field(sample, predictor) -> np.ndarray:
    _, field = accepted_cx3d_standard(sample, predictor)
    return np.asarray(field, dtype=np.float32)


def standard_identity_error(sample, predictor, field_builder) -> float:
    _, accepted = accepted_cx3d_standard(sample, predictor)
    field = field_builder(sample, predictor)
    return float(np.max(np.abs(np.asarray(field, dtype=np.float32) - np.asarray(accepted, dtype=np.float32))))


def _sample2d(arr: np.ndarray, x: float, y: float, resolution: float) -> float:
    gx = int(np.clip(np.floor(float(x) / max(float(resolution), 1e-6)), 0, arr.shape[1] - 1))
    gy = int(np.clip(np.floor(float(y) / max(float(resolution), 1e-6)), 0, arr.shape[0] - 1))
    return float(arr[gy, gx])


def _bin_idx(value: float, bins: tuple[float, ...]) -> int:
    for idx, thr in enumerate(bins):
        if float(value) <= float(thr):
            return int(idx)
    return int(len(bins))


def state_signature(case: dict[str, Any], bundle: dict[str, Any], state: tuple[float, float, float], spec: SignatureSpec) -> tuple[int, ...]:
    bundle = augmented_bundle(bundle)
    x, y, yaw = map(float, state)
    gx, gy, _ = map(float, case['goal'])
    dist = float(math.hypot(gx - x, gy - y))
    goal_dir = float(math.atan2(gy - y, gx - x))
    heading_cos = float(math.cos(goal_dir - yaw))
    clearance = _sample2d(np.maximum(case['esdf'], 0.0).astype(np.float32), x, y, float(case['resolution']))
    trap = _sample2d(np.asarray(bundle['_cx14_trap'], dtype=np.float32), x, y, float(case['resolution']))
    corridor = _sample2d(np.asarray(bundle['_cx14_corridor_score'], dtype=np.float32), x, y, float(case['resolution']))
    yaw_bin = int(np.floor(((yaw + math.pi) / (2.0 * math.pi)) * float(spec.yaw_bins))) % int(spec.yaw_bins)
    return (
        _bin_idx(clearance, spec.clearance_bins),
        _bin_idx(dist, spec.dist_bins),
        _bin_idx(heading_cos, spec.heading_bins),
        _bin_idx(trap, spec.trap_bins),
        _bin_idx(corridor, spec.corridor_bins),
        int(yaw_bin),
    )


def novelty_count(search_state: dict[str, Any], key: tuple[int, ...], slot: str) -> int:
    table = search_state.setdefault(slot, {})
    return int(table.get(tuple(key), 0))


def increment_novelty(search_state: dict[str, Any], key: tuple[int, ...], slot: str) -> None:
    table = search_state.setdefault(slot, {})
    table[tuple(key)] = int(table.get(tuple(key), 0)) + 1


def current_progress(case: dict[str, Any], field: np.ndarray, record, records: dict[Any, Any], *, depth: int = 1) -> float:
    cur = record
    vals = []
    for _ in range(int(max(depth, 0))):
        parent_key = getattr(cur, 'parent', None)
        if parent_key is None or parent_key not in records:
            break
        parent = records[parent_key]
        vals.append(float(parent.anchor) - float(cur.anchor))
        cur = parent
    if not vals:
        return 0.0
    return float(np.mean(vals))


def compare_plan_to_baseline(baseline, plan, prep_ms: float = 0.0) -> dict[str, float]:
    total_ms = float(getattr(plan, 'runtime_ms', 0.0)) + float(prep_ms)
    return {
        'success_delta': float(getattr(plan, 'success', 0.0)) - float(getattr(baseline, 'success', 0.0)),
        'exp_delta': float(getattr(baseline, 'expansions', 0.0)) - float(getattr(plan, 'expansions', 0.0)),
        'time_delta_ms': float(getattr(baseline, 'runtime_ms', 0.0)) - float(total_ms),
        'time_overhead_ratio': (float(total_ms) - float(getattr(baseline, 'runtime_ms', 0.0))) / max(float(getattr(baseline, 'runtime_ms', 0.0)), 1e-6),
    }


__all__ = [
    'SignatureSpec',
    'BucketFeatures',
    'BucketSpec',
    'EpisodeBucketEncoder',
    'augmented_bundle',
    'build_nonholonomic_field',
    'build_standard_field',
    'compare_plan_to_baseline',
    'corridor_score_map',
    'current_progress',
    'increment_novelty',
    'novelty_count',
    'run_hybrid_with_policy',
    'standard_identity_error',
    'state_signature',
    'trap_score_map',
]
