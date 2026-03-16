from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx4.common import accepted_cx3d_nonholonomic, accepted_cx3d_standard
from rs_cx8.common import primitive_index_from_case, run_hybrid_with_policy
from rs_cx14.common import BucketSpec, EpisodeBucketEncoder, augmented_bundle, current_progress, standard_identity_error
from utils.common import bilinear_interpolate, wrap_to_pi


@dataclass(frozen=True)
class RecoverabilitySpec:
    stride_cells: int = 2
    yaw_stride: int = 2
    ray_step_m: float = 0.35
    ray_horizon_steps: int = 6
    clearance_clip_m: float = 2.5
    goal_dist_clip_m: float = 20.0


@dataclass(frozen=True)
class RecoverabilityStats:
    key: tuple[int, int, int]
    clearance: float
    trap: float
    corridor: float
    forward_clearance: float
    reverse_clearance: float
    left_clearance: float
    right_clearance: float
    goal_distance: float
    heading_cos: float
    heading_abs: float


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg) -> tuple[dict[str, Any], np.ndarray]:
    bundle, field = accepted_cx3d_nonholonomic(case, predictor, cfg)
    return augmented_bundle(bundle), np.asarray(field, dtype=np.float32)


def build_standard_field(sample, predictor) -> np.ndarray:
    _, field = accepted_cx3d_standard(sample, predictor)
    return np.asarray(field, dtype=np.float32)


def _sample2d(arr: np.ndarray, x: float, y: float, resolution: float) -> float:
    return float(bilinear_interpolate(np.asarray(arr, dtype=np.float32), float(x), float(y), float(resolution)))


def primitive_family(candidate) -> str:
    steer = float(candidate.steer)
    direction = int(candidate.direction)
    turn = 'L' if steer < -1e-6 else ('R' if steer > 1e-6 else 'S')
    travel = 'F' if direction > 0 else 'B'
    return f'{travel}-{turn}'


def primitive_family_from_index(case: dict[str, Any], primitive_index: int) -> str:
    pindex = primitive_index_from_case(case)
    label = pindex.label(int(primitive_index))
    return str(label)


def primitive_group(family: str) -> str:
    fam = str(family)
    if fam.startswith('B-'):
        return 'reverse'
    if fam.endswith('-S'):
        return 'straight'
    return 'forward_turn'


class RecoverabilityEncoder:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], spec: RecoverabilitySpec) -> None:
        self.case = case
        self.bundle = augmented_bundle(bundle)
        self.spec = spec
        self.resolution = float(case['resolution'])
        self.bucket = EpisodeBucketEncoder(case, self.bundle, BucketSpec(int(spec.stride_cells), int(spec.yaw_stride)))
        self.vehicle_clearance = 0.35 * float(case['vehicle'].width)
        self.esdf = np.maximum(np.asarray(case['esdf'], dtype=np.float32), 0.0)
        self.width = int(self.esdf.shape[1])
        self.height = int(self.esdf.shape[0])
        self.dir_cache: dict[tuple[int, int, int], tuple[float, float, float, float]] = {}
        self.static_score_cache: dict[tuple[int, int, int], float] = {}

    def _bucket_center(self, key: tuple[int, int, int]) -> tuple[float, float, float]:
        stride = max(int(self.spec.stride_cells), 1)
        yaw_stride = max(int(self.spec.yaw_stride), 1)
        bx, by, byaw = key
        gx = float(min(max(bx * stride + stride * 0.5, 0.0), self.width - 1.0))
        gy = float(min(max(by * stride + stride * 0.5, 0.0), self.height - 1.0))
        yaw_bins = 8
        yaw_idx = float(byaw * yaw_stride + 0.5 * yaw_stride)
        yaw = wrap_to_pi((yaw_idx / float(yaw_bins)) * 2.0 * math.pi - math.pi)
        return gx * self.resolution, gy * self.resolution, float(yaw)

    def bucket_center(self, key: tuple[int, int, int]) -> tuple[float, float, float]:
        return self._bucket_center(tuple(key))

    def _ray_clearance(self, x: float, y: float, yaw: float) -> float:
        best = 0.0
        for step_idx in range(1, int(max(self.spec.ray_horizon_steps, 1)) + 1):
            dist = float(step_idx) * float(self.spec.ray_step_m)
            px = float(x) + dist * math.cos(float(yaw))
            py = float(y) + dist * math.sin(float(yaw))
            if px < 0.0 or py < 0.0 or px >= self.width * self.resolution or py >= self.height * self.resolution:
                break
            clearance = _sample2d(self.esdf, px, py, self.resolution)
            if clearance <= float(self.vehicle_clearance):
                break
            best = dist
        return float(best)

    def _directionals(self, key: tuple[int, int, int]) -> tuple[float, float, float, float]:
        cached = self.dir_cache.get(tuple(key), None)
        if cached is not None:
            return cached
        x, y, yaw = self._bucket_center(tuple(key))
        out = (
            self._ray_clearance(x, y, yaw),
            self._ray_clearance(x, y, wrap_to_pi(yaw + math.pi)),
            self._ray_clearance(x, y, wrap_to_pi(yaw + 0.5 * math.pi)),
            self._ray_clearance(x, y, wrap_to_pi(yaw - 0.5 * math.pi)),
        )
        self.dir_cache[tuple(key)] = out
        return out

    def features(self, state: tuple[float, float, float]) -> RecoverabilityStats:
        feat = self.bucket.features(state)
        forward_clearance, reverse_clearance, left_clearance, right_clearance = self._directionals(feat.key)
        x, y, yaw = map(float, state)
        gx, gy, _ = map(float, self.case['goal'])
        goal_dx = float(gx - x)
        goal_dy = float(gy - y)
        goal_distance = float(math.hypot(goal_dx, goal_dy))
        goal_dir = float(math.atan2(goal_dy, goal_dx))
        heading_err = wrap_to_pi(goal_dir - yaw)
        heading_cos = float(math.cos(heading_err))
        return RecoverabilityStats(
            key=tuple(feat.key),
            clearance=float(feat.clearance),
            trap=float(feat.trap),
            corridor=float(feat.corridor),
            forward_clearance=float(forward_clearance),
            reverse_clearance=float(reverse_clearance),
            left_clearance=float(left_clearance),
            right_clearance=float(right_clearance),
            goal_distance=float(goal_distance),
            heading_cos=float(heading_cos),
            heading_abs=float(abs(heading_err)),
        )

    def features_many(self, states: list[tuple[float, float, float]]) -> list[RecoverabilityStats]:
        return [self.features(tuple(map(float, state))) for state in states]

    def static_surface(self, key: tuple[int, int, int]) -> float:
        cached = self.static_score_cache.get(tuple(key), None)
        if cached is not None:
            return float(cached)
        feat = self.bucket.features(self._bucket_center(tuple(key)))
        fwd, rev, left, right = self._directionals(tuple(key))
        score = (
            0.24 * normalize_clip(float(feat.clearance), float(self.spec.clearance_clip_m))
            + 0.22 * float(feat.corridor)
            + 0.18 * normalize_clip(float(max(rev, left, right)), float(self.spec.ray_step_m * self.spec.ray_horizon_steps))
            + 0.12 * normalize_clip(float(fwd), float(self.spec.ray_step_m * self.spec.ray_horizon_steps))
            - 0.28 * float(feat.trap)
        )
        self.static_score_cache[tuple(key)] = float(score)
        return float(score)

    def best_border_key(self, key: tuple[int, int, int], radius: int) -> tuple[int, int, int] | None:
        cur = self.static_surface(tuple(key))
        best_key = None
        best_score = cur + 1e-6
        bx, by, byaw = map(int, key)
        for dx in range(-int(radius), int(radius) + 1):
            for dy in range(-int(radius), int(radius) + 1):
                if dx == 0 and dy == 0:
                    continue
                cand = (bx + dx, by + dy, byaw)
                score = self.static_surface(cand) - 0.08 * float(abs(dx) + abs(dy))
                if score > best_score:
                    best_score = float(score)
                    best_key = tuple(cand)
        return best_key


def normalize_clip(value: float, clip: float) -> float:
    return float(np.clip(float(value) / max(float(clip), 1e-6), 0.0, 1.0))


def recoverability_margin(
    stats: RecoverabilityStats,
    *,
    clearance_w: float,
    corridor_w: float,
    trap_w: float,
    reverse_w: float,
    lateral_w: float,
    forward_w: float,
    heading_w: float,
    spec: RecoverabilitySpec,
) -> float:
    horizon = float(spec.ray_step_m * spec.ray_horizon_steps)
    return float(
        clearance_w * normalize_clip(stats.clearance, spec.clearance_clip_m)
        + corridor_w * float(stats.corridor)
        + reverse_w * normalize_clip(stats.reverse_clearance, horizon)
        + lateral_w * normalize_clip(max(stats.left_clearance, stats.right_clearance), horizon)
        + forward_w * normalize_clip(stats.forward_clearance, horizon)
        - trap_w * float(stats.trap)
        - heading_w * float(max(0.0, -stats.heading_cos))
    )


def reverse_need_score(stats: RecoverabilityStats, spec: RecoverabilitySpec) -> float:
    horizon = float(spec.ray_step_m * spec.ray_horizon_steps)
    reverse_norm = normalize_clip(stats.reverse_clearance, horizon)
    forward_norm = normalize_clip(stats.forward_clearance, horizon)
    return float(max(0.0, reverse_norm - forward_norm) * max(0.0, -stats.heading_cos) * (0.5 + float(stats.trap)))


def margin_key(stats: RecoverabilityStats) -> tuple[int, int, int, int, int]:
    return (
        int(np.clip(np.floor(normalize_clip(stats.clearance, 2.5) * 4.0), 0, 4)),
        int(np.clip(np.floor(float(stats.trap) * 4.0), 0, 4)),
        int(np.clip(np.floor(float(stats.corridor) * 4.0), 0, 4)),
        int(np.clip(np.floor(normalize_clip(stats.reverse_clearance, 2.1) * 4.0), 0, 4)),
        int(np.clip(np.floor((float(stats.heading_cos) + 1.0) * 2.0), 0, 4)),
    )


def read_slot_counter(search_state: dict[str, Any], slot: str, key: tuple[int, ...]) -> int:
    table = search_state.get(slot, None)
    if not isinstance(table, dict):
        return 0
    return int(table.get(tuple(key), 0))


def increment_slot_counter(search_state: dict[str, Any], slot: str, key: tuple[int, ...]) -> int:
    table = search_state.get(slot, None)
    if not isinstance(table, dict):
        table = {}
        search_state[slot] = table
    nxt = int(table.get(tuple(key), 0)) + 1
    table[tuple(key)] = int(nxt)
    return int(nxt)


def update_global_stall(search_state: dict[str, Any], slot: str, event_hit: bool) -> int:
    cur = int(search_state.get(slot, 0))
    cur = cur + 1 if bool(event_hit) else max(0, cur - 1)
    search_state[slot] = int(cur)
    return int(cur)


def extract_escape_motifs(
    train_assets: list[dict[str, Any]],
    spec: RecoverabilitySpec,
    *,
    trap_threshold: float,
    min_gain: float,
    horizon_steps: int,
) -> dict[tuple[int, int, int, int, int], dict[str, Any]]:
    motifs: dict[tuple[int, int, int, int, int], dict[str, Any]] = {}
    for asset in train_assets:
        path = np.asarray(asset['baseline_result'].path, dtype=np.float32)
        trace = list(asset.get('trace', []))
        if path.shape[0] < 3 or not trace:
            continue
        encoder = RecoverabilityEncoder(asset['case'], asset['bundle'], spec)
        scores = []
        stats_list: list[RecoverabilityStats] = []
        for idx in range(path.shape[0]):
            stats = encoder.features(tuple(float(v) for v in path[idx]))
            stats_list.append(stats)
            score = recoverability_margin(
                stats,
                clearance_w=0.22,
                corridor_w=0.22,
                trap_w=0.28,
                reverse_w=0.18,
                lateral_w=0.10,
                forward_w=0.08,
                heading_w=0.08,
                spec=spec,
            )
            scores.append(float(score))
        for idx in range(min(len(trace), len(scores) - 1)):
            cur_stats = stats_list[idx]
            if float(cur_stats.trap) < float(trap_threshold):
                continue
            best_gain = 0.0
            for nxt in range(idx + 1, min(idx + 1 + int(horizon_steps), len(scores))):
                gain = float(scores[nxt]) - float(scores[idx])
                if gain > best_gain:
                    best_gain = float(gain)
            if best_gain < float(min_gain):
                continue
            key = margin_key(cur_stats)
            family = primitive_family_from_index(asset['case'], int(trace[idx]))
            entry = motifs.get(key, None)
            if entry is None:
                entry = {'counts': {}, 'gain_sum': 0.0, 'num_hits': 0}
                motifs[key] = entry
            counts = entry['counts']
            counts[str(family)] = int(counts.get(str(family), 0)) + 1
            entry['gain_sum'] = float(entry['gain_sum']) + float(best_gain)
            entry['num_hits'] = int(entry['num_hits']) + 1
    out: dict[tuple[int, int, int, int, int], dict[str, Any]] = {}
    for key, entry in motifs.items():
        counts = dict(entry['counts'])
        if not counts:
            continue
        family = max(counts.items(), key=lambda item: (int(item[1]), item[0]))[0]
        out[tuple(key)] = {
            'family': str(family),
            'num_hits': int(entry['num_hits']),
            'avg_gain': float(entry['gain_sum']) / max(int(entry['num_hits']), 1),
        }
    return out


def save_meta(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')


__all__ = [
    'RecoverabilitySpec',
    'RecoverabilityStats',
    'RecoverabilityEncoder',
    'accepted_cx3d_nonholonomic',
    'build_nonholonomic_field',
    'build_standard_field',
    'current_progress',
    'extract_escape_motifs',
    'increment_slot_counter',
    'margin_key',
    'normalize_clip',
    'primitive_family',
    'primitive_family_from_index',
    'primitive_group',
    'read_slot_counter',
    'recoverability_margin',
    'reverse_need_score',
    'run_hybrid_with_policy',
    'save_meta',
    'standard_identity_error',
    'update_global_stall',
]
