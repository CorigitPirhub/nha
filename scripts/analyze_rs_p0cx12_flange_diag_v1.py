from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from network.inference import NeuralHeuristicPredictor
from rs_cx.common import CXGlobalConfig
from rs_cx10 import cx10_d_las
from rs_cx11.common import best_mode_progress, load_base_params, proposal_context
from rs_cx10.common import load_teacher_memory
from rs_cx8.common import load_nonholonomic_assets, load_nonholonomic_contexts, write_inputs_sha256


def _read_split_csv(path: Path) -> list[Path]:
    with path.open('r', newline='', encoding='utf-8') as f:
        return [Path(r['path']) for r in csv.DictReader(f)]


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open('r', newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames = []
    seen = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def _public_exp_delta_map(path: Path, dataset: str = 'exp4') -> dict[str, float]:
    rows = _read_csv(path)
    grouped = defaultdict(dict)
    for row in rows:
        if str(row['dataset']) != str(dataset):
            continue
        grouped[str(row['sample_name'])][str(row['method'])] = row
    out = {}
    for sample, methods in grouped.items():
        base = methods.get('CX3-D')
        full = methods.get('CX10-D (Full)')
        if base is None or full is None:
            continue
        out[sample] = float(base['expansions']) - float(full['expansions'])
    return out


def _calib_exp_delta_map(path: Path) -> dict[str, float]:
    rows = _read_csv(path)
    return {str(r['sample_name']): float(r['exp_delta']) for r in rows}


def _scenario_map(files: list[Path]) -> dict[str, str]:
    out = {}
    for p in files:
        with np.load(p, allow_pickle=False) as z:
            out[p.name] = str(z['scenario'])
    return out


def _diag_row(ctx: dict[str, Any], exp_delta: float, source: str, dataset: str) -> dict[str, Any]:
    case = ctx['case']
    bundle = ctx['bundle']
    field = ctx['field']
    proposal = proposal_context(BASE_MEMORY, BASE_PARAMS, case, bundle, field, DEVICE)
    gates = proposal['gates']
    top_gate = proposal['top_gate']
    if top_gate is not None:
        feat = np.asarray(top_gate['compact_feature'], dtype=np.float32)
        inner_mode = int(top_gate.get('inner_mode', 0))
        outer_mode = int(top_gate.get('outer_mode', 0))
        exit_visibility = best_mode_progress(case, field, top_gate['state'], inner_mode) if inner_mode > 0 else float('-inf')
        setup_progress = best_mode_progress(case, field, top_gate['state'], outer_mode) if outer_mode > 0 else float('-inf')
        trap_proxy = float(max(0.0, (setup_progress if np.isfinite(setup_progress) else 0.0) - max(exit_visibility, 0.0))) * float(max(feat[9] - 0.50, 0.0)) * float(feat[19])
        exit_clearance = float(feat[6]) * max(0.5, max(exit_visibility, 0.0) + 0.5)
        goal_heading = float(feat[22])
        row = {
            'sample_name': str(ctx['path'].name),
            'source': source,
            'dataset': dataset,
            'scenario': str(case['scenario']),
            'exp_delta': float(exp_delta),
            'num_gates': int(len(gates)),
            'top_gate_score': float(top_gate.get('score', 0.0)),
            'top_gate_inner_mode': int(inner_mode),
            'top_gate_outer_mode': int(outer_mode),
            'clearance': float(feat[6]),
            'corridor_width': float(feat[10]),
            'corridor_conf': float(feat[9]),
            'heading_to_goal_cos': goal_heading,
            'goal_dist': float(feat[0]),
            'reverse_escape': float(feat[17]),
            'forward_escape': float(feat[18]),
            'bottleneck': float(feat[19]),
            'curvature_slack': float(feat[24]),
            'scene_hard': float(feat[13]),
            'scene_misc': float(feat[14]),
            'scene_bridge': float(feat[15]),
            'scene_open': float(feat[16]),
            'exit_visibility': float(exit_visibility if np.isfinite(exit_visibility) else -1e6),
            'setup_progress': float(setup_progress if np.isfinite(setup_progress) else -1e6),
            'trap_proxy': float(trap_proxy),
            'exit_clearance_proxy': float(exit_clearance),
        }
    else:
        row = {
            'sample_name': str(ctx['path'].name),
            'source': source,
            'dataset': dataset,
            'scenario': str(case['scenario']),
            'exp_delta': float(exp_delta),
            'num_gates': 0,
            'top_gate_score': 0.0,
            'top_gate_inner_mode': 0,
            'top_gate_outer_mode': 0,
            'clearance': 0.0,
            'corridor_width': 0.0,
            'corridor_conf': 0.0,
            'heading_to_goal_cos': 0.0,
            'goal_dist': 0.0,
            'reverse_escape': 0.0,
            'forward_escape': 0.0,
            'bottleneck': 0.0,
            'curvature_slack': 0.0,
            'scene_hard': float(proposal['scene_feature'][0]),
            'scene_misc': float(proposal['scene_feature'][1]),
            'scene_bridge': float(proposal['scene_feature'][2]),
            'scene_open': float(proposal['scene_feature'][3]),
            'exit_visibility': -1e6,
            'setup_progress': -1e6,
            'trap_proxy': 0.0,
            'exit_clearance_proxy': 0.0,
        }
    return row


def _range_summary(rows: list[dict[str, Any]], features: list[str]) -> list[dict[str, Any]]:
    out = []
    for feat in features:
        vals = np.asarray([float(r[feat]) for r in rows], dtype=np.float32)
        out.append({
            'feature': feat,
            'min': float(np.min(vals)) if vals.size else float('nan'),
            'max': float(np.max(vals)) if vals.size else float('nan'),
            'mean': float(np.mean(vals)) if vals.size else float('nan'),
            'std': float(np.std(vals)) if vals.size else float('nan'),
        })
    return out


def _overlap_summary(flange_rows: list[dict[str, Any]], narrow_rows: list[dict[str, Any]], features: list[str]) -> list[dict[str, Any]]:
    out = []
    for feat in features:
        fvals = np.asarray([float(r[feat]) for r in flange_rows], dtype=np.float32)
        nvals = np.asarray([float(r[feat]) for r in narrow_rows], dtype=np.float32)
        if fvals.size == 0 or nvals.size == 0:
            continue
        fmin, fmax = float(np.min(fvals)), float(np.max(fvals))
        nmin, nmax = float(np.min(nvals)), float(np.max(nvals))
        overlap = max(0.0, min(fmax, nmax) - max(fmin, nmin))
        total = max(fmax, nmax) - min(fmin, nmin)
        out.append({
            'feature': feat,
            'flange_min': fmin,
            'flange_max': fmax,
            'narrow_min': nmin,
            'narrow_max': nmax,
            'range_overlap': overlap,
            'normalized_overlap': float(overlap / total) if total > 1e-6 else 0.0,
            'mean_gap': float(np.mean(nvals) - np.mean(fvals)),
        })
    return out


def main() -> None:
    out_root = ROOT / 'outputs/rs_p0cx12_design_scout_v1'
    out_root.mkdir(parents=True, exist_ok=True)

    predictor = NeuralHeuristicPredictor(ROOT / 'outputs/checkpoints/exp3_final_manual_v11b.pt', device=DEVICE, gaussian_sigma=2.5)
    cfg = CXGlobalConfig()

    train_files = _read_split_csv(ROOT / 'data/split/calib_hard_v1/calib_train.csv')
    val_files = _read_split_csv(ROOT / 'data/split/calib_hard_v1/calib_val.csv')
    public_files = sorted((ROOT / 'data/benchmark/parasol_narrow/test').glob('sample_*.npz'))

    train_assets = load_nonholonomic_assets(train_files, predictor, cfg, 20000, tag='cx12:base-refit-train')
    val_assets = load_nonholonomic_assets(val_files, predictor, cfg, 20000, tag='cx12:base-refit-val')
    contexts = load_nonholonomic_contexts(list(dict.fromkeys(val_files + public_files)), predictor, cfg, tag='cx12:contexts')
    ctx_map = {str(item['path'].name): item for item in contexts}

    global BASE_MEMORY, BASE_PARAMS
    BASE_PARAMS = load_base_params(ROOT / 'outputs/rs_p0cx10_d_pilot_v1/chosen.json')
    teacher_memory = load_teacher_memory(ROOT / 'outputs/rs_p0cx8_d_hard_pilot_v1/chosen.json', 'cpu')
    teacher_memory['device'] = 'cpu'
    BASE_MEMORY = cx10_d_las.fit_variant(
        train_assets,
        val_assets,
        predictor,
        cfg,
        BASE_PARAMS,
        out_root / 'base_refit',
        DEVICE,
        dependencies={
            'teacher_memory': teacher_memory,
            'teacher_chosen_json': ROOT / 'outputs/rs_p0cx8_d_hard_pilot_v1/chosen.json',
        },
    )

    calib_delta = _calib_exp_delta_map(ROOT / 'outputs/rs_p0cx10_d_pilot_v1/calib_val_case_rows.csv')
    public_delta = _public_exp_delta_map(ROOT / 'outputs/rs_p0cx10_d_pilot_v1/public_case_rows.csv', dataset='exp4')

    calib_rows = []
    for sample, delta in calib_delta.items():
        ctx = ctx_map.get(sample)
        if ctx is None:
            continue
        calib_rows.append(_diag_row(ctx, delta, source='calib_hard_v1', dataset='calib_val'))

    public_rows = []
    for sample, delta in public_delta.items():
        ctx = ctx_map.get(sample)
        if ctx is None:
            continue
        public_rows.append(_diag_row(ctx, delta, source='parasol_narrow_public', dataset='exp4_public'))

    _write_csv(out_root / 'calib_feature_rows.csv', calib_rows)
    _write_csv(out_root / 'public_feature_rows.csv', public_rows)

    calib_flange = sorted([r for r in calib_rows if r['scenario'] == 'flange'], key=lambda r: float(r['exp_delta']))
    calib_narrow = sorted([r for r in calib_rows if r['scenario'] == 'narrow_passage'], key=lambda r: float(r['exp_delta']), reverse=True)
    public_flange = sorted([r for r in public_rows if r['scenario'] == 'flange'], key=lambda r: float(r['exp_delta']))[:5]
    public_narrow = sorted([r for r in public_rows if r['scenario'] == 'narrow_passage'], key=lambda r: float(r['exp_delta']), reverse=True)[:5]

    _write_csv(out_root / 'worst_public_flange_top5.csv', public_flange)
    _write_csv(out_root / 'best_public_narrow_top5.csv', public_narrow)
    _write_csv(out_root / 'calib_flange_rows.csv', calib_flange)
    _write_csv(out_root / 'calib_narrow_rows.csv', calib_narrow)

    features = [
        'clearance', 'corridor_width', 'corridor_conf', 'heading_to_goal_cos', 'goal_dist',
        'reverse_escape', 'forward_escape', 'bottleneck', 'curvature_slack', 'scene_hard',
        'scene_misc', 'scene_bridge', 'scene_open', 'exit_visibility', 'setup_progress',
        'trap_proxy', 'exit_clearance_proxy',
    ]
    overlap = _overlap_summary(public_flange, public_narrow, features)
    _write_csv(out_root / 'feature_overlap_public_flange_vs_narrow.csv', overlap)
    _write_csv(out_root / 'feature_summary_public_flange.csv', _range_summary(public_flange, features))
    _write_csv(out_root / 'feature_summary_public_narrow.csv', _range_summary(public_narrow, features))

    inputs = [
        ROOT / 'outputs/rs_p0cx10_d_pilot_v1/chosen.json',
        ROOT / 'outputs/rs_p0cx10_d_pilot_v1/calib_val_case_rows.csv',
        ROOT / 'outputs/rs_p0cx10_d_pilot_v1/public_case_rows.csv',
        ROOT / 'outputs/checkpoints/exp3_final_manual_v11b.pt',
        ROOT / 'data/split/calib_hard_v1/calib_train.csv',
        ROOT / 'data/split/calib_hard_v1/calib_val.csv',
    ] + train_files + val_files + public_files
    write_inputs_sha256(inputs, out_root / 'inputs_sha256.json')
    manifest = {
        'version': 'rs_p0cx12_design_diag_v1',
        'base_chosen_json': 'outputs/rs_p0cx10_d_pilot_v1/chosen.json',
        'inputs_sha256': json.loads((out_root / 'inputs_sha256.json').read_text(encoding='utf-8')),
        'calib_flange_count': len(calib_flange),
        'calib_narrow_count': len(calib_narrow),
        'public_flange_count': len(public_flange),
        'public_narrow_count': len(public_narrow),
    }
    (out_root / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')

    print('wrote', out_root)
    print('calib_flange', len(calib_flange), 'calib_narrow', len(calib_narrow), 'public_flange', len(public_flange), 'public_narrow', len(public_narrow))


DEVICE = 'cuda'
BASE_MEMORY: dict[str, Any]
BASE_PARAMS: Any

if __name__ == '__main__':
    main()
