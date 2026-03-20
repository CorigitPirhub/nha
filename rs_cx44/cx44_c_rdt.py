from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx23.common import class_key
from rs_cx27.common import coarse_state_key, scene_kind
from rs_cx44 import cx44_b_fcwt as parent_mod


@dataclass(frozen=True)
class CX44CRDTParams:
    review_cell_stride: int
    review_yaw_bins: int
    margin_thr: float
    anchor_eps: float
    enable_parasol_misc: bool
    enable_deadend_labyrinth: bool
    enable_narrow_passage: bool
    min_redundancy: int


def param_grid() -> list[CX44CRDTParams]:
    return [
        CX44CRDTParams(3, 12, 0.03, 0.02, True, True, True, 2),
        CX44CRDTParams(3, 12, 0.03, 0.02, True, True, True, 3),
        CX44CRDTParams(3, 12, 0.03, 0.02, True, True, False, 2),
        CX44CRDTParams(3, 12, 0.03, 0.02, True, False, False, 2),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {'name': 'No-Witness-Transfer', 'disable_witness_transfer': True},
        {'name': 'Proxy-Only-Negative', 'force_negative_skip': True},
    ]


def _load_parent_params() -> parent_mod.parent_mod.parent_mod.CX34AMSRParams:
    data = json.loads(Path('outputs/rs_p0cx34_a_pilot_v1/chosen.json').read_text(encoding='utf-8'))
    return parent_mod.parent_mod.parent_mod.CX34AMSRParams(**data['params'])


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX44CRDTParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    parent_params = _load_parent_params()
    parent_memory = parent_mod.parent_mod.parent_mod.fit_variant(calib_train_assets, calib_val_assets, predictor, cfg, parent_params, out_dir / 'parent_fit', device, dependencies)
    sig_counter: Counter[tuple[Any, ...]] = Counter()
    for asset in calib_train_assets:
        scenario = str(asset['case'].get('scenario', ''))
        enabled = (
            (bool(params.enable_parasol_misc) and scenario == 'parasol_misc')
            or (bool(params.enable_deadend_labyrinth) and scenario == 'deadend_labyrinth')
            or (bool(params.enable_narrow_passage) and scenario == 'narrow_passage')
        )
        if not enabled:
            continue
        field = parent_mod.parent_mod.parent_mod.build_nonholonomic_field(asset['case'], predictor, cfg, parent_params, parent_memory)
        bundle = asset['case'].get('_cx21_bundle', asset['bundle'])
        policy = parent_mod.parent_mod.parent_mod.make_policy(parent_memory, parent_params, asset['case'], bundle, field, device, ablation=None)
        baseline = asset['baseline_result']
        path = np.asarray(baseline.path, dtype=np.float32)
        if path.shape[0] < 2:
            continue
        search_state: dict[str, Any] = {}
        for state in path[:-1]:
            from types import SimpleNamespace
            rec = SimpleNamespace(x=float(state[0]), y=float(state[1]), yaw=float(state[2]), anchor=float(0.0))
            ctx = policy.prepare_expand(None, rec, None, None, None, None, search_state, None)
            if not isinstance(ctx, dict):
                continue
            sig = (
                str(scene_kind(asset['case'], bundle)),
                str(class_key(ctx)),
                tuple(
                    coarse_state_key(
                        rec,
                        asset['case'],
                        cell_stride=int(params.review_cell_stride),
                        yaw_bins=int(params.review_yaw_bins),
                    )
                ),
                int(bool(ctx.get('must_precede', False))),
                int(len(list(ctx.get('macros', []))) > 0),
            )
            sig_counter[sig] += 1
    out_dir.mkdir(parents=True, exist_ok=True)
    serializable = [{'sig': list(sig[:2]) + [list(sig[2]), sig[3], sig[4]], 'count': int(count)} for sig, count in sig_counter.items() if int(count) >= int(params.min_redundancy)]
    (out_dir / 'cx44_c_meta.json').write_text(json.dumps({'params': params.__dict__, 'eligible_signature_count': int(sum(int(v) >= int(params.min_redundancy) for v in sig_counter.values())), 'eligible_signatures': serializable[:200]}, indent=2, ensure_ascii=False), encoding='utf-8')
    return {'parent_params': parent_params, 'parent_memory': parent_memory, 'signature_counter': dict(sig_counter)}


class RDTPolicy(parent_mod.FCWTPolicy):
    def __init__(
        self,
        case: dict[str, Any],
        bundle: dict[str, Any],
        field: np.ndarray,
        parent_params,
        parent_memory: dict[str, Any],
        params: CX44CRDTParams,
        signature_counter: dict[tuple[Any, ...], int],
        *,
        disable_witness_transfer: bool = False,
        force_negative_skip: bool = False,
    ) -> None:
        super().__init__(
            case,
            bundle,
            field,
            parent_params,
            parent_memory,
            parent_mod.CX44BFCWTParams(
                review_cell_stride=int(params.review_cell_stride),
                review_yaw_bins=int(params.review_yaw_bins),
                margin_thr=float(params.margin_thr),
                anchor_eps=float(params.anchor_eps),
                enable_parasol_misc=bool(params.enable_parasol_misc),
                enable_deadend_labyrinth=bool(params.enable_deadend_labyrinth),
                enable_narrow_passage=bool(params.enable_narrow_passage),
            ),
            disable_witness_transfer=disable_witness_transfer,
            force_negative_skip=force_negative_skip,
        )
        self.min_redundancy = int(params.min_redundancy)
        self.signature_counter = dict(signature_counter)
        self.stats['redundancy_reject'] = 0.0
        self.stats['redundancy_pass'] = 0.0

    def _family_active(self) -> bool:
        return super()._family_active()

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if not self._family_active():
            self.stats['family_gate_bypass'] = float(self.stats.get('family_gate_bypass', 0.0) + 1.0)
            return self.base.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        if not isinstance(node_ctx, dict):
            self.stats['family_gate_bypass'] = float(self.stats.get('family_gate_bypass', 0.0) + 1.0)
            return self.base.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        sig = self._sig(record, node_ctx)
        count = int(self.signature_counter.get(sig, 0))
        if int(count) < int(self.min_redundancy):
            self.stats['family_gate_hits'] = float(self.stats.get('family_gate_hits', 0.0) + 1.0)
            self.stats['redundancy_reject'] = float(self.stats.get('redundancy_reject', 0.0) + 1.0)
            return self.base.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        self.stats['family_gate_hits'] = float(self.stats.get('family_gate_hits', 0.0) + 1.0)
        self.stats['redundancy_pass'] = float(self.stats.get('redundancy_pass', 0.0) + 1.0)
        return super(parent_mod.FCWTPolicy, self).extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)


def make_policy(memory: dict[str, Any], params: CX44CRDTParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    policy = RDTPolicy(
        case,
        bundle,
        field,
        memory['parent_params'],
        memory['parent_memory'],
        params,
        memory['signature_counter'],
        disable_witness_transfer=bool(ablation.get('disable_witness_transfer', False)),
        force_negative_skip=bool(ablation.get('force_negative_skip', False)),
    )
    policy.enable_diagnostics = bool(ablation.get('enable_diagnostics', False))
    return policy


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX44CRDTParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return parent_mod.parent_mod.parent_mod.build_nonholonomic_field(case, predictor, cfg, memory['parent_params'], memory['parent_memory'])


def build_standard_field(sample, predictor, params: CX44CRDTParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return parent_mod.parent_mod.parent_mod.build_standard_field(sample, predictor, memory['parent_params'], memory['parent_memory']).astype(np.float32)
