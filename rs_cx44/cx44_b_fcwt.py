from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx44 import cx44_a_rmrc as parent_mod


TARGET_SCENARIOS = ('parasol_misc', 'deadend_labyrinth', 'narrow_passage')


@dataclass(frozen=True)
class CX44BFCWTParams:
    review_cell_stride: int
    review_yaw_bins: int
    margin_thr: float
    anchor_eps: float
    enable_parasol_misc: bool
    enable_deadend_labyrinth: bool
    enable_narrow_passage: bool


def param_grid() -> list[CX44BFCWTParams]:
    return [
        CX44BFCWTParams(3, 12, 0.03, 0.02, True, True, True),
        CX44BFCWTParams(3, 12, 0.03, 0.02, True, True, False),
        CX44BFCWTParams(3, 12, 0.03, 0.02, True, False, False),
        CX44BFCWTParams(3, 12, 0.04, 0.02, True, True, False),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {'name': 'No-Witness-Transfer', 'disable_witness_transfer': True},
        {'name': 'Proxy-Only-Negative', 'force_negative_skip': True},
    ]


def _load_parent_params() -> parent_mod.parent_mod.CX34AMSRParams:
    data = json.loads(Path('outputs/rs_p0cx34_a_pilot_v1/chosen.json').read_text(encoding='utf-8'))
    return parent_mod.parent_mod.CX34AMSRParams(**data['params'])


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX44BFCWTParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    parent_params = _load_parent_params()
    parent_memory = parent_mod.parent_mod.fit_variant(calib_train_assets, calib_val_assets, predictor, cfg, parent_params, out_dir / 'parent_fit', device, dependencies)
    out_dir.mkdir(parents=True, exist_ok=True)
    target_scenarios = []
    if bool(params.enable_parasol_misc):
        target_scenarios.append('parasol_misc')
    if bool(params.enable_deadend_labyrinth):
        target_scenarios.append('deadend_labyrinth')
    if bool(params.enable_narrow_passage):
        target_scenarios.append('narrow_passage')
    (out_dir / 'cx44_b_meta.json').write_text(json.dumps({'params': params.__dict__, 'target_scenarios': target_scenarios}, indent=2, ensure_ascii=False), encoding='utf-8')
    return {'parent_params': parent_params, 'parent_memory': parent_memory}


class FCWTPolicy(parent_mod.RMRCPPolicy):
    def __init__(
        self,
        case: dict[str, Any],
        bundle: dict[str, Any],
        field: np.ndarray,
        parent_params,
        parent_memory: dict[str, Any],
        params: CX44BFCWTParams,
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
            parent_mod.CX44ARMRCParams(
                review_cell_stride=int(params.review_cell_stride),
                review_yaw_bins=int(params.review_yaw_bins),
                margin_thr=float(params.margin_thr),
                anchor_eps=float(params.anchor_eps),
            ),
            disable_witness_transfer=disable_witness_transfer,
            force_negative_skip=force_negative_skip,
        )
        self.stats['family_gate_hits'] = 0.0
        self.stats['family_gate_bypass'] = 0.0
        self._target_scenarios = set()
        if bool(params.enable_parasol_misc):
            self._target_scenarios.add('parasol_misc')
        if bool(params.enable_deadend_labyrinth):
            self._target_scenarios.add('deadend_labyrinth')
        if bool(params.enable_narrow_passage):
            self._target_scenarios.add('narrow_passage')

    def _family_active(self) -> bool:
        return bool(str(self.case.get('scenario', '')) in self._target_scenarios)

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if not self._family_active():
            self.stats['family_gate_bypass'] = float(self.stats.get('family_gate_bypass', 0.0) + 1.0)
            return self.base.extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)
        self.stats['family_gate_hits'] = float(self.stats.get('family_gate_hits', 0.0) + 1.0)
        return super().extra_successors(planner, record, goal, records, candidates, node_ctx, search_state, h_pair)


def make_policy(memory: dict[str, Any], params: CX44BFCWTParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    policy = FCWTPolicy(
        case,
        bundle,
        field,
        memory['parent_params'],
        memory['parent_memory'],
        params,
        disable_witness_transfer=bool(ablation.get('disable_witness_transfer', False)),
        force_negative_skip=bool(ablation.get('force_negative_skip', False)),
    )
    policy.enable_diagnostics = bool(ablation.get('enable_diagnostics', False))
    return policy


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX44BFCWTParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return parent_mod.parent_mod.build_nonholonomic_field(case, predictor, cfg, memory['parent_params'], memory['parent_memory'])


def build_standard_field(sample, predictor, params: CX44BFCWTParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return parent_mod.parent_mod.build_standard_field(sample, predictor, memory['parent_params'], memory['parent_memory']).astype(np.float32)
