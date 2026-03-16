from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx14.common import (
    BucketSpec,
    EpisodeBucketEncoder,
    augmented_bundle,
    build_nonholonomic_field as build_base_field,
    build_standard_field as build_base_standard_field,
    current_progress,
)


@dataclass(frozen=True)
class CX14BLHUParams:
    base_penalty: float
    update_gain: float
    activation_progress_threshold: float
    stall_threshold: float
    accept_ratio_threshold: float
    trap_weight: float
    corridor_bonus: float
    repeat_trigger: int
    global_stall_trigger: int
    stride_cells: int
    yaw_stride: int
    progress_depth: int
    max_penalty: float


def param_grid() -> list[CX14BLHUParams]:
    return [
        CX14BLHUParams(0.03, 0.10, 0.008, 0.012, 0.30, 0.030, 0.010, 1, 1, 2, 2, 1, 0.24),
        CX14BLHUParams(0.04, 0.12, 0.008, 0.015, 0.28, 0.035, 0.010, 1, 1, 2, 2, 1, 0.26),
        CX14BLHUParams(0.04, 0.14, 0.010, 0.018, 0.25, 0.040, 0.012, 1, 2, 2, 2, 1, 0.28),
        CX14BLHUParams(0.05, 0.14, 0.012, 0.020, 0.25, 0.045, 0.015, 2, 2, 2, 2, 2, 0.30),
        CX14BLHUParams(0.05, 0.16, 0.015, 0.022, 0.22, 0.050, 0.015, 2, 2, 3, 2, 2, 0.32),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {'name': 'No-Update', 'disable_update': True},
        {'name': 'Always-Active', 'disable_event_trigger': True},
    ]


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX14BLHUParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'lhu_meta.json').write_text(json.dumps({'params': params.__dict__}, indent=2, ensure_ascii=False), encoding='utf-8')
    return {'best_val_loss': float('nan')}


class LHUPolicy:
    def __init__(
        self,
        case: dict[str, Any],
        bundle: dict[str, Any],
        field: np.ndarray,
        params: CX14BLHUParams,
        disable_update: bool = False,
        disable_event_trigger: bool = False,
    ) -> None:
        self.case = case
        self.bundle = augmented_bundle(bundle)
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_update = bool(disable_update)
        self.disable_event_trigger = bool(disable_event_trigger)
        self.encoder = EpisodeBucketEncoder(
            case,
            self.bundle,
            BucketSpec(
                stride_cells=int(self.params.stride_cells),
                yaw_stride=int(self.params.yaw_stride),
            ),
        )
        self.penalty_slot = '_cx14_lhu_penalty'
        self.seen_slot = '_cx14_lhu_seen'
        self.global_stall_slot = '_cx14_lhu_global_stall'

    def _read_table(self, search_state: dict[str, Any], slot: str) -> dict[tuple[int, ...], float] | dict[tuple[int, ...], int] | None:
        table = search_state.get(slot, None)
        return table if isinstance(table, dict) else None

    def _read_penalty(self, search_state: dict[str, Any], key: tuple[int, ...]) -> float:
        table = self._read_table(search_state, self.penalty_slot)
        if table is None:
            return 0.0
        return float(table.get(tuple(key), 0.0))

    def _add_penalty(self, search_state: dict[str, Any], key: tuple[int, ...], val: float) -> None:
        table = search_state.get(self.penalty_slot, None)
        if not isinstance(table, dict):
            table = {}
            search_state[self.penalty_slot] = table
        cur = float(table.get(tuple(key), 0.0))
        table[tuple(key)] = float(np.clip(cur + float(val), 0.0, float(self.params.max_penalty)))

    def _read_seen(self, search_state: dict[str, Any], key: tuple[int, ...]) -> int:
        table = self._read_table(search_state, self.seen_slot)
        if table is None:
            return 0
        return int(table.get(tuple(key), 0))

    def _inc_seen(self, search_state: dict[str, Any], key: tuple[int, ...]) -> int:
        table = search_state.get(self.seen_slot, None)
        if not isinstance(table, dict):
            table = {}
            search_state[self.seen_slot] = table
        nxt = int(table.get(tuple(key), 0)) + 1
        table[tuple(key)] = int(nxt)
        return int(nxt)

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        feat = self.encoder.features((float(record.x), float(record.y), float(record.yaw)))
        seen = self._read_seen(search_state, feat.key)
        progress = current_progress(self.case, self.field, record, records, depth=int(max(self.params.progress_depth, 1)))
        global_stall = int(search_state.get(self.global_stall_slot, 0))
        active = bool(self.disable_event_trigger)
        if not active:
            active = bool(
                seen >= int(self.params.repeat_trigger)
                or global_stall >= int(self.params.global_stall_trigger)
                or float(progress) <= float(self.params.activation_progress_threshold)
            )
        return {
            'bucket_key': feat.key,
            'progress': float(progress),
            'active': bool(active),
            'seen': int(seen),
        }

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if not isinstance(node_ctx, dict) or not bool(node_ctx.get('active', False)):
            return None
        feat_list = self.encoder.features_many([cand.next_state for cand in candidates])
        ranked = []
        for cand, feat in zip(candidates, feat_list):
            delta = float(self.params.base_penalty) + self._read_penalty(search_state, feat.key)
            delta += float(self.params.trap_weight) * float(feat.trap)
            delta -= float(self.params.corridor_bonus) * float(feat.corridor)
            ranked.append((cand, {'priority_secondary_delta': float(delta)}))
        ranked.sort(key=lambda item: float(item[1]['priority_secondary_delta']))
        return ranked

    def complete_expand(self, planner, record, goal, records, node_ctx, invalid_local, valid_local, accepted_local, search_state, h_pair):
        if not isinstance(node_ctx, dict):
            return
        key = node_ctx.get('bucket_key', None)
        if key is None:
            return
        seen = self._inc_seen(search_state, tuple(key))
        progress = float(node_ctx.get('progress', 0.0))
        accept_ratio = float(accepted_local) / max(float(valid_local), 1.0)
        event_hit = bool(
            float(progress) <= float(self.params.stall_threshold)
            or int(accepted_local) == 0
            or accept_ratio <= float(self.params.accept_ratio_threshold)
        )
        if event_hit:
            search_state[self.global_stall_slot] = int(search_state.get(self.global_stall_slot, 0)) + 1
        else:
            search_state[self.global_stall_slot] = max(0, int(search_state.get(self.global_stall_slot, 0)) - 1)
        if self.disable_update or not event_hit:
            return
        gain = float(self.params.update_gain)
        if int(accepted_local) == 0:
            gain *= 1.25
        if float(progress) <= float(self.params.stall_threshold):
            gain *= 1.10
        if int(seen) >= int(self.params.repeat_trigger):
            gain *= 1.10
        self._add_penalty(search_state, tuple(key), gain)


def make_policy(memory: dict[str, Any], params: CX14BLHUParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return LHUPolicy(
        case,
        bundle,
        field,
        params,
        disable_update=bool(ablation.get('disable_update', False)),
        disable_event_trigger=bool(ablation.get('disable_event_trigger', False)),
    )


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX14BLHUParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    bundle, field = build_base_field(case, predictor, cfg)
    case['_cx14_bundle'] = bundle
    return field.astype(np.float32)


def build_standard_field(sample, predictor, params: CX14BLHUParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return build_base_standard_field(sample, predictor).astype(np.float32)
