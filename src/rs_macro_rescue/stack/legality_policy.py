from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_macro_rescue.stack.base import CXGlobalConfig
from rs_macro_rescue.stack.legality import (
    CVFModeConfig,
    FAMILY_BUCKETS,
    RecoverabilityEncoder,
    RecoverabilitySpec,
    build_nonholonomic_field as build_base_field,
    build_standard_field as build_base_standard_field,
    compile_family_support,
    compile_macro_library,
    compile_mode_support,
    compile_viability_table,
    consistency_score,
    consistent_mode,
    family_bucket_name,
    foundation_feature_vector,
    foundation_state,
    macro_family,
    macro_successor_candidates,
    margin_key,
    match_mode_support,
    query_viability_table,
    save_meta,
    serializable_family_support,
)
from rs_macro_rescue.stack.support import support_match


@dataclass(frozen=True)
class CX21BLAGParams:
    support_slack: float
    allowed_bonus: float
    discouraged_penalty: float
    forbidden_penalty: float
    macro_bonus: float
    must_precede_bonus: float
    improve_gain: float
    hard_forbid_hits: int
    max_macros: int
    forward_viability_thr: float
    reverse_required_thr: float
    trap_high_thr: float
    escape_affinity_low_thr: float
    hopeless_viability_thr: float
    stride_cells: int
    yaw_stride: int
    horizon_steps: int


def param_grid() -> list[CX21BLAGParams]:
    return [
        CX21BLAGParams(0.18, 0.08, 0.06, 0.10, 0.08, 0.10, 0.14, 6, 3, 0.34, 0.08, 0.56, -0.02, 0.10, 2, 2, 5),
        CX21BLAGParams(0.20, 0.10, 0.08, 0.12, 0.10, 0.12, 0.16, 5, 3, 0.32, 0.07, 0.54, 0.00, 0.08, 2, 2, 5),
        CX21BLAGParams(0.22, 0.12, 0.10, 0.14, 0.12, 0.14, 0.18, 4, 4, 0.30, 0.06, 0.50, 0.02, 0.06, 2, 2, 6),
    ]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {'name': 'No-Legality', 'disable_legality': True},
        {'name': 'Soft-Only', 'soft_only': True},
        {'name': 'No-Must-Precede', 'disable_must_precede': True},
    ]


def _mode_cfg(params: CX21BLAGParams) -> CVFModeConfig:
    return CVFModeConfig(
        forward_viability_thr=float(params.forward_viability_thr),
        reverse_required_thr=float(params.reverse_required_thr),
        trap_high_thr=float(params.trap_high_thr),
        escape_affinity_low_thr=float(params.escape_affinity_low_thr),
        hopeless_viability_thr=float(params.hopeless_viability_thr),
    )


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX21BLAGParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    spec = RecoverabilitySpec(stride_cells=int(params.stride_cells), yaw_stride=int(params.yaw_stride))
    mode_cfg = _mode_cfg(params)
    table = compile_viability_table(calib_train_assets, spec, horizon_steps=int(params.horizon_steps), min_samples=3)
    mode_support = compile_mode_support(calib_train_assets, spec, mode_cfg, horizon_steps=int(params.horizon_steps), min_gain=0.08)
    macros = compile_macro_library(calib_train_assets, spec, horizon_steps=int(params.horizon_steps), min_gain=0.08, max_macros=max(int(params.max_macros) * 2, 4))
    family_support = compile_family_support(calib_train_assets, spec, mode_cfg, horizon_steps=int(params.horizon_steps), min_gain=0.08)
    save_meta(
        out_dir / 'lag_meta.json',
        {
            'params': params.__dict__,
            'mode_cfg': mode_cfg.__dict__,
            'mode_support': {mode: {'similarity_floor': float(band.similarity_floor), 'min_progress': float(band.min_progress), 'counts': int(band.counts)} for mode, band in mode_support.items()},
            'family_support': serializable_family_support(family_support),
            'macros': [m.__dict__ for m in macros],
        },
    )
    return {'viability_table': table, 'mode_support': mode_support, 'family_support': family_support, 'macros': macros, 'best_val_loss': float('nan')}


def _derive_rules(mode: str, feat: np.ndarray, gain_hint: float, family_support: dict[str, dict[str, Any]], params: CX21BLAGParams) -> tuple[dict[str, str], dict[str, float], bool]:
    rules: dict[str, str] = {bucket: 'discouraged' for bucket in FAMILY_BUCKETS}
    conf: dict[str, float] = {bucket: 0.0 for bucket in FAMILY_BUCKETS}
    mapping = family_support.get(str(mode), {})
    matched_families: set[str] = set()
    for bucket in FAMILY_BUCKETS:
        stat = mapping.get(bucket, None)
        if stat is None:
            continue
        matched, sim = support_match(stat.band, feat, float(gain_hint), slack=float(params.support_slack))
        if matched:
            matched_families.add(bucket)
            conf[bucket] = float(sim)
    must_precede = bool(mode == 'reverse_setup')
    if mode == 'forward_safe':
        rules['straight'] = 'allowed'
        rules['forward_turn'] = 'allowed'
        rules['reverse'] = 'discouraged'
        rules['reverse_setup'] = 'discouraged'
        if 'straight' in matched_families and mapping.get('reverse', None) is not None and int(mapping['reverse'].hits) >= int(params.hard_forbid_hits):
            rules['reverse'] = 'forbidden'
    elif mode == 'reverse_setup':
        rules['reverse'] = 'allowed'
        rules['reverse_setup'] = 'allowed'
        rules['forward_turn'] = 'discouraged'
        rules['straight'] = 'forbidden'
    elif mode == 'escape_border':
        rules['reverse'] = 'allowed'
        rules['reverse_setup'] = 'allowed'
        rules['forward_turn'] = 'allowed' if 'forward_turn' in matched_families else 'discouraged'
        rules['straight'] = 'forbidden' if 'straight' not in matched_families else 'discouraged'
    else:
        rules = {bucket: 'discouraged' for bucket in FAMILY_BUCKETS}
    for bucket in matched_families:
        if rules[bucket] == 'discouraged':
            rules[bucket] = 'allowed'
    return rules, conf, must_precede


class LAGPolicy:
    def __init__(self, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, params: CX21BLAGParams, memory: dict[str, Any], disable_legality: bool = False, soft_only: bool = False, disable_must_precede: bool = False) -> None:
        self.case = case
        self.field = np.asarray(field, dtype=np.float32)
        self.params = params
        self.disable_legality = bool(disable_legality)
        self.soft_only = bool(soft_only)
        self.disable_must_precede = bool(disable_must_precede)
        self.spec = RecoverabilitySpec(stride_cells=int(params.stride_cells), yaw_stride=int(params.yaw_stride))
        self.mode_cfg = _mode_cfg(params)
        self.encoder = RecoverabilityEncoder(case, bundle, self.spec)
        self.table = dict(memory.get('viability_table', {})) if isinstance(memory, dict) else {}
        self.mode_support = dict(memory.get('mode_support', {})) if isinstance(memory, dict) else {}
        self.family_support = dict(memory.get('family_support', {})) if isinstance(memory, dict) else {}
        self.macros = list(memory.get('macros', [])) if isinstance(memory, dict) else []

    def prepare_expand(self, planner, record, goal, records, open_heap, anchor_heap, search_state, h_pair):
        state = (float(record.x), float(record.y), float(record.yaw))
        cur = foundation_state(self.case, self.case.get('_cx21_bundle', {}), self.field, self.encoder, state, self.spec)
        stats = self.encoder.features(state)
        oracle = query_viability_table(self.table, margin_key(stats))
        oracle_gain = float(oracle.get('avg_future_gain', 0.0)) if isinstance(oracle, dict) else 0.0
        feat = foundation_feature_vector(cur)
        support_mode, matched, _ = match_mode_support(self.mode_support, feat, gain_hint=max(float(oracle_gain), 0.0), slack=float(self.params.support_slack))
        mode = str(support_mode if bool(matched) else consistent_mode(cur, self.mode_cfg))
        rules, conf, must_precede = _derive_rules(mode, feat, max(float(oracle_gain), 0.0), self.family_support, self.params)
        allowed_families = {fam for fam, label in rules.items() if label == 'allowed'}
        if self.disable_legality:
            chosen_macros = list(self.macros[: int(max(self.params.max_macros, 0))])
        else:
            chosen_macros = []
            for macro in self.macros:
                bucket = family_bucket_name(str(macro.family))
                if bool(must_precede) and not bool(self.disable_must_precede):
                    if bucket not in {'reverse', 'reverse_setup'}:
                        continue
                elif bucket not in allowed_families:
                    continue
                chosen_macros.append(macro)
                if len(chosen_macros) >= int(max(self.params.max_macros, 0)):
                    break
        return {
            'foundation': cur,
            'mode': mode,
            'rules': rules,
            'conf': conf,
            'must_precede': bool(must_precede and not self.disable_must_precede),
            'macros': chosen_macros,
        }

    def extra_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if not isinstance(node_ctx, dict):
            return []
        macros = list(node_ctx.get('macros', []))
        if not macros:
            return []
        return macro_successor_candidates(self.case, planner, record, h_pair, macros, max_macros=len(macros))

    def rank_successors(self, planner, record, goal, records, candidates, node_ctx, search_state, h_pair):
        if not isinstance(node_ctx, dict):
            return None
        current = node_ctx.get('foundation')
        if current is None:
            return None
        rules = dict(node_ctx.get('rules', {}))
        conf = dict(node_ctx.get('conf', {}))
        must_precede = bool(node_ctx.get('must_precede', False))
        current_cost = float(current.cost_to_go)
        current_viability = float(current.viability)
        labels = [rules.get(family_bucket_name(macro_family(cand)), 'discouraged') for cand in candidates]
        num_non_forbidden = int(sum(label != 'forbidden' for label in labels))
        ranked = []
        for cand, label in zip(candidates, labels):
            fam_bucket = family_bucket_name(macro_family(cand))
            nf = foundation_state(self.case, self.case.get('_cx21_bundle', {}), self.field, self.encoder, cand.next_state, self.spec)
            cons = float(consistency_score(nf))
            delta = 0.0
            delta += float(self.params.improve_gain) * float(nf.cost_to_go - current_cost)
            delta -= 0.04 * float(nf.viability - current_viability)
            if getattr(cand, 'source', 'primitive') == 'macro':
                delta -= float(self.params.macro_bonus)
            if label == 'allowed':
                delta -= float(self.params.allowed_bonus) * float(cons)
            elif label == 'discouraged':
                delta += float(self.params.discouraged_penalty) * float(cons)
            elif label == 'forbidden':
                delta += float(self.params.forbidden_penalty) * float(cons)
            if must_precede:
                if fam_bucket in {'reverse', 'reverse_setup'} and int(cand.direction) < 0:
                    delta -= float(self.params.must_precede_bonus)
                elif fam_bucket in {'straight', 'forward_turn'} and int(cand.direction) > 0:
                    delta += float(self.params.must_precede_bonus)
            skip = False
            if (
                not self.disable_legality
                and not self.soft_only
                and label == 'forbidden'
                and getattr(cand, 'source', 'primitive') == 'macro'
                and num_non_forbidden >= 2
                and float(conf.get(fam_bucket, 0.0)) >= 0.0
            ):
                skip = True
            ranked.append((cand, {'skip': bool(skip), 'priority_secondary_delta': float(delta)}))
        ranked.sort(key=lambda item: float(item[1]['priority_secondary_delta']))
        return ranked


def make_policy(memory: dict[str, Any], params: CX21BLAGParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    return LAGPolicy(
        case,
        bundle,
        field,
        params,
        memory,
        disable_legality=bool(ablation.get('disable_legality', False)),
        soft_only=bool(ablation.get('soft_only', False)),
        disable_must_precede=bool(ablation.get('disable_must_precede', False)),
    )


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX21BLAGParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    bundle, field = build_base_field(case, predictor, cfg)
    case['_cx21_bundle'] = bundle
    return field.astype(np.float32)


def build_standard_field(sample, predictor, params: CX21BLAGParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return build_base_standard_field(sample, predictor).astype(np.float32)
