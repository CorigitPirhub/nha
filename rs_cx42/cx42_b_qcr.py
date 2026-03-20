from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from rs_cx.common import CXGlobalConfig
from rs_cx11.common import SupportBand, fit_support_band, support_match
from rs_cx34 import cx34_a_msr as cx34_mod
from rs_cx41 import cx41_b_fdr as cx41_mod


@dataclass(frozen=True)
class QueryCompatContract:
    positive_support: SupportBand | None
    negative_support: SupportBand | None
    gain_floor: float
    positive_hits: int
    negative_hits: int


@dataclass(frozen=True)
class CX42BQCRParams:
    min_hits: int


def param_grid() -> list[CX42BQCRParams]:
    return [CX42BQCRParams(min_hits=2)]


def ablation_specs() -> list[dict[str, Any]]:
    return [
        {'name': 'Always-CX34', 'force_branch': 'cx34'},
        {'name': 'Always-CX41', 'force_branch': 'cx41'},
    ]


def _scene_feature(bundle: dict[str, Any], scenario: str) -> np.ndarray:
    scene = dict(bundle.get('scene', {}))
    return np.asarray(
        [
            float(1.0 if str(scenario) == 'parasol_misc' else 0.0),
            float(1.0 if str(scenario) == 'maze' else 0.0),
            float(1.0 if str(scenario) == 'narrow_passage' else 0.0),
            float(1.0 if str(scenario) == 'flange' else 0.0),
            float(scene.get('hard_likelihood', 0.0)),
            float(scene.get('misc_likelihood', 0.0)),
            float(scene.get('bridge_diffuse', 0.0)),
            float(scene.get('focus_gap', 0.0)),
            float(scene.get('path_openness', 0.0)),
            float(scene.get('barrier_peak', 0.0)),
        ],
        dtype=np.float32,
    )


def _path_len(plan) -> float:
    path = np.asarray(plan.path, dtype=np.float32)
    if path.size <= 0 or path.shape[0] < 2:
        return float('nan')
    xy = path[:, :2]
    return float(np.sum(np.linalg.norm(xy[1:] - xy[:-1], axis=1)))


def _safe_and_faster(base_plan, alt_plan, base_time_ms: float, alt_time_ms: float) -> tuple[bool, float]:
    same_success = float(base_plan.success) == float(alt_plan.success)
    non_worse_exp = float(alt_plan.expansions) <= float(base_plan.expansions)
    non_worse_path = float(_path_len(alt_plan)) <= float(_path_len(base_plan)) + 1e-6 if np.isfinite(_path_len(base_plan)) and np.isfinite(_path_len(alt_plan)) else True
    faster = float(alt_time_ms) < float(base_time_ms)
    gain = (float(base_time_ms) - float(alt_time_ms)) / max(float(base_time_ms), 1e-6)
    return bool(same_success and non_worse_exp and non_worse_path and faster), float(gain)


def fit_variant(calib_train_assets, calib_val_assets, predictor, cfg: CXGlobalConfig, params: CX42BQCRParams, out_dir: Path, device: str, dependencies: dict[str, Any] | None = None) -> dict[str, Any]:
    teacher = dependencies['haa_teacher'] if isinstance(dependencies, dict) and 'haa_teacher' in dependencies else None
    cx34_params = cx34_mod.CX34AMSRParams(**json.loads(Path('outputs/rs_p0cx34_a_pilot_v1/chosen.json').read_text())['params'])
    cx41_params = cx41_mod.CX41BFDRParams(**json.loads(Path('outputs/rs_p0cx41_b_pilot_v1/chosen.json').read_text())['params'])
    cx34_mem = cx34_mod.fit_variant(calib_train_assets, calib_val_assets, predictor, cfg, cx34_params, out_dir / 'cx34_fit', device, {'haa_teacher': teacher} if teacher is not None else None)
    cx41_mem = cx41_mod.fit_variant(calib_train_assets, calib_val_assets, predictor, cfg, cx41_params, out_dir / 'cx41_fit', device, {'haa_teacher': teacher} if teacher is not None else None)

    pos_feats: list[np.ndarray] = []
    pos_gain: list[float] = []
    neg_feats: list[np.ndarray] = []
    neg_gain: list[float] = []
    for asset in calib_train_assets:
        case = asset['case']
        bundle = asset['case'].get('_cx21_bundle', asset['bundle'])
        field34 = cx34_mod.build_nonholonomic_field(case, predictor, cfg, cx34_params, cx34_mem)
        field41 = cx41_mod.build_nonholonomic_field(case, predictor, cfg, cx41_params, cx41_mem)
        policy34 = cx34_mod.make_policy(cx34_mem, cx34_params, case, bundle, field34, device, ablation=None)
        policy41 = cx41_mod.make_policy(cx41_mem, cx41_params, case, bundle, field41, device, ablation=None)
        import time
        t0 = time.perf_counter(); plan34 = __import__('rs_cx21.common', fromlist=['run_hybrid_with_policy']).run_hybrid_with_policy(case, field34, 20000, successor_policy=policy34, record_expanded=False); t34 = plan34.runtime_ms + (time.perf_counter()-t0)*1000.0*0
        t0 = time.perf_counter(); plan41 = __import__('rs_cx21.common', fromlist=['run_hybrid_with_policy']).run_hybrid_with_policy(case, field41, 20000, successor_policy=policy41, record_expanded=False); t41 = plan41.runtime_ms + (time.perf_counter()-t0)*1000.0*0
        feat = _scene_feature(bundle, str(case['scenario']))
        good, gain = _safe_and_faster(plan34, plan41, float(t34), float(t41))
        if good:
            pos_feats.append(feat); pos_gain.append(gain)
        else:
            neg_feats.append(feat); neg_gain.append(gain)
    pos_band = fit_support_band(pos_feats, pos_gain, low_q=0.05, high_q=0.95, sim_q=0.15) if pos_feats else None
    neg_band = fit_support_band(neg_feats, neg_gain, low_q=0.05, high_q=0.95, sim_q=0.15) if neg_feats else None
    gain_floor = float(np.quantile(np.asarray(pos_gain, dtype=np.float32), 0.05)) if pos_gain else 0.0
    contract = QueryCompatContract(pos_band, neg_band, gain_floor, len(pos_feats), len(neg_feats))
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'cx42_b_meta.json').write_text(json.dumps({'params': params.__dict__, 'contract': {'positive_hits': contract.positive_hits, 'negative_hits': contract.negative_hits, 'gain_floor': contract.gain_floor}}, indent=2, ensure_ascii=False), encoding='utf-8')
    return {'cx34_params': cx34_params, 'cx34_memory': cx34_mem, 'cx41_params': cx41_params, 'cx41_memory': cx41_mem, 'contract': contract}


def _choose_branch(case: dict[str, Any], bundle: dict[str, Any], contract: QueryCompatContract, force_branch: str | None = None) -> str:
    if force_branch in {'cx34', 'cx41'}:
        return force_branch
    feat = _scene_feature(bundle, str(case['scenario']))
    pos_match, pos_sim = support_match(contract.positive_support, feat, float(contract.gain_floor), slack=0.0)
    neg_match, neg_sim = support_match(contract.negative_support, feat, float(contract.gain_floor), slack=0.0)
    if bool(pos_match and not neg_match):
        return 'cx41'
    return 'cx34'


class QCRPolicy:
    def __init__(self, policy, branch: str) -> None:
        self.policy = policy
        self.branch = branch

    def start_search(self, *args, **kwargs):
        if hasattr(self.policy, 'start_search'):
            return self.policy.start_search(*args, **kwargs)

    def prepare_expand(self, *args, **kwargs):
        return self.policy.prepare_expand(*args, **kwargs)

    def extra_successors(self, *args, **kwargs):
        return self.policy.extra_successors(*args, **kwargs)

    def rank_successors(self, *args, **kwargs):
        return self.policy.rank_successors(*args, **kwargs)

    def complete_expand(self, *args, **kwargs):
        if hasattr(self.policy, 'complete_expand'):
            return self.policy.complete_expand(*args, **kwargs)


def make_policy(memory: dict[str, Any], params: CX42BQCRParams, case: dict[str, Any], bundle: dict[str, Any], field: np.ndarray, device: str, ablation: dict[str, Any] | None = None):
    ablation = ablation if isinstance(ablation, dict) else {}
    branch = _choose_branch(case, bundle, memory['contract'], force_branch=ablation.get('force_branch'))
    if branch == 'cx41':
        policy = cx41_mod.make_policy(memory['cx41_memory'], memory['cx41_params'], case, bundle, field, device, ablation=None)
    else:
        policy = cx34_mod.make_policy(memory['cx34_memory'], memory['cx34_params'], case, bundle, field, device, ablation=None)
    return QCRPolicy(policy, branch)


def build_nonholonomic_field(case: dict[str, Any], predictor, cfg: CXGlobalConfig, params: CX42BQCRParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    # both branches preserve the accepted CX3-D standard audit; use CX34 field path as default
    return cx34_mod.build_nonholonomic_field(case, predictor, cfg, memory['cx34_params'], memory['cx34_memory'])


def build_standard_field(sample, predictor, params: CX42BQCRParams, memory: dict[str, Any] | None = None) -> np.ndarray:
    return cx34_mod.build_standard_field(sample, predictor, memory['cx34_params'], memory['cx34_memory']).astype(np.float32)

