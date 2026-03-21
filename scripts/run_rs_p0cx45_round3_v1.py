from __future__ import annotations

import argparse
import csv
import importlib
import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baselines.common import load_grid_sample
from network.inference import NeuralHeuristicPredictor
from rs_cx.common import CXGlobalConfig
from rs_cx21.common import run_hybrid_with_policy, standard_identity_error
from rs_cx8.common import load_nonholonomic_assets, load_nonholonomic_contexts, write_inputs_sha256


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Run P0-CX45 round3 macro-bearing evidence witness pilots.')
    p.add_argument('--split-root', type=Path, default=Path('data/split/calib_hard_v1'))
    p.add_argument('--parasol-root', type=Path, default=Path('data/benchmark/parasol_narrow/test'))
    p.add_argument('--benchmark-root', type=Path, default=Path('data/benchmark'))
    p.add_argument('--ours-checkpoint', type=Path, default=Path('outputs/checkpoints/exp3_final_manual_v11b.pt'))
    p.add_argument('--device', type=str, default='cuda')
    p.add_argument('--dev-cap', type=int, default=20000)
    p.add_argument('--exp4-cap', type=int, default=20000)
    p.add_argument('--max-mp-cases', type=int, default=800)
    p.add_argument('--max-csm-cases', type=int, default=400)
    p.add_argument('--outputs-root', type=Path, default=Path('outputs/rs_p0cx45_c_pilot_v1'))
    p.add_argument('--reports-root', type=Path, default=Path('reports'))
    return p.parse_args()


def _read_split_rows(path: Path) -> list[dict[str, Any]]:
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


def _summary(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[tuple(row[k] for k in keys)].append(row)
    out = []
    for key, grp in sorted(grouped.items()):
        item = {k: key[i] for i, k in enumerate(keys)}
        item.update({'num_cases': len(grp), 'success_rate': float(np.mean([float(r['success']) for r in grp])), 'avg_expansions': float(np.mean([float(r['expansions']) for r in grp])), 'avg_time_ms': float(np.mean([float(r['time_ms']) for r in grp]))})
        out.append(item)
    return out


def _delta(summary_rows: list[dict[str, Any]], group_keys: tuple[str, ...], baseline_method: str) -> list[dict[str, Any]]:
    grouped = defaultdict(dict)
    for row in summary_rows:
        grouped[tuple(row[k] for k in group_keys)][str(row['method'])] = row
    out = []
    for grp, methods in sorted(grouped.items()):
        base = methods.get(baseline_method)
        if base is None:
            continue
        for method, row in methods.items():
            if method == baseline_method:
                continue
            item = {k: grp[i] for i, k in enumerate(group_keys)}
            item.update({'method': method, 'baseline': baseline_method, 'success_delta_pp': 100.0 * (float(row['success_rate']) - float(base['success_rate'])), 'exp_delta': float(base['avg_expansions']) - float(row['avg_expansions']), 'mean_time_overhead_ratio': (float(row['avg_time_ms']) - float(base['avg_time_ms'])) / max(float(base['avg_time_ms']), 1e-6)})
            out.append(item)
    return out


def _family_delta(rows: list[dict[str, Any]], baseline_method: str) -> list[dict[str, Any]]:
    return _delta(_summary(rows, ('dataset', 'scenario', 'method')), ('dataset', 'scenario'), baseline_method)


def _eval_variant(mod, memory, params_obj, predictor, cfg, assets, cap, device, method_name, *, ablation=None):
    rows = []
    total = len(assets)
    for idx, asset in enumerate(assets, start=1):
        asset['case']['_cx44_sample_name'] = str(asset['path'].name)
        field = mod.build_nonholonomic_field(asset['case'], predictor, cfg, params_obj, memory)
        bundle = asset['case'].get('_cx21_bundle', asset['bundle'])
        prep_t0 = time.perf_counter()
        policy = mod.make_policy(memory, params_obj, asset['case'], bundle, field, device, ablation=ablation)
        prep_ms = (time.perf_counter() - prep_t0) * 1000.0
        plan = run_hybrid_with_policy(asset['case'], field, int(cap), successor_policy=policy, record_expanded=False)
        stats = dict(getattr(policy, 'stats', {}))
        rows.append({'dataset': 'exp4', 'sample_name': str(asset['path'].name), 'scenario': str(asset['case']['scenario']), 'method': method_name, 'success': float(plan.success), 'expansions': float(plan.expansions), 'time_ms': float(plan.runtime_ms + prep_ms), 'witness_hits': float(stats.get('witness_hits', 0.0)), 'eaw_skip_hits': float(stats.get('eaw_skip_hits', 0.0)), 'family_gate_hits': float(stats.get('family_gate_hits', 0.0)), 'family_gate_bypass': float(stats.get('family_gate_bypass', 0.0))})
        if idx % 5 == 0 or idx == total:
            print(f'[{method_name}] {idx}/{total}', flush=True)
    return rows


def _eval_cx3(public_contexts, cap: int):
    rows = []
    total = len(public_contexts)
    for idx, asset in enumerate(public_contexts, start=1):
        plan = run_hybrid_with_policy(asset['case'], asset['field'], int(cap), successor_policy=None, record_expanded=False)
        rows.append({'dataset': 'exp4', 'sample_name': str(asset['path'].name), 'scenario': str(asset['case']['scenario']), 'method': 'CX3-D', 'success': float(plan.success), 'expansions': float(plan.expansions), 'time_ms': float(plan.runtime_ms)})
        if idx % 5 == 0 or idx == total:
            print(f'[CX3-D] {idx}/{total}', flush=True)
    return rows


def _standard_audit(mod, memory, params_obj, predictor, benchmark_root: Path, max_mp_cases: int, max_csm_cases: int):
    rows = []
    for dataset, limit in [('mp', int(max_mp_cases)), ('csm', int(max_csm_cases))]:
        files = sorted((benchmark_root / dataset / 'test').glob('sample_*.npz'))[:limit]
        diffs = []
        for idx, path in enumerate(files, start=1):
            sample = load_grid_sample(path)
            diffs.append(standard_identity_error(sample, predictor, lambda s, p: mod.build_standard_field(s, p, params_obj, memory)))
            if idx % 100 == 0 or idx == len(files):
                print(f'[cx45c:standard:{dataset}] {idx}/{len(files)}', flush=True)
        rows.append({'dataset': dataset, 'num_cases': int(len(files)), 'max_abs_field_diff': float(max(diffs) if diffs else 0.0), 'mean_abs_field_diff': float(np.mean(diffs) if diffs else 0.0)})
    return rows


def main() -> None:
    args = parse_args()
    args.outputs_root.mkdir(parents=True, exist_ok=True)
    args.reports_root.mkdir(parents=True, exist_ok=True)

    mod = importlib.import_module('rs_cx45.cx45_c_mbeaw')
    parent_mod = importlib.import_module('rs_cx34.cx34_a_msr')
    compat_mod = importlib.import_module('rs_cx41.cx41_b_fdr')

    predictor = NeuralHeuristicPredictor(args.ours_checkpoint, device=args.device, gaussian_sigma=2.5)
    cfg = CXGlobalConfig()
    train_rows = _read_split_rows(args.split_root / 'calib_train.csv')
    val_rows = _read_split_rows(args.split_root / 'calib_val.csv')
    train_files = [Path(r['path']) for r in train_rows]
    val_files = [Path(r['path']) for r in val_rows]
    public_files = sorted(args.parasol_root.glob('sample_*.npz'))
    train_assets = load_nonholonomic_assets(train_files, predictor, cfg, int(args.dev_cap), tag='cx45c:calib-train')
    val_contexts = load_nonholonomic_contexts(val_files, predictor, cfg, tag='cx45c:calib-val')
    public_contexts = load_nonholonomic_contexts(public_files, predictor, cfg, tag='cx45c:public')

    parent_params = parent_mod.CX34AMSRParams(**json.loads(Path('outputs/rs_p0cx34_a_pilot_v1/chosen.json').read_text(encoding='utf-8'))['params'])
    compat_params = compat_mod.CX41BFDRParams(**json.loads(Path('outputs/rs_p0cx41_b_pilot_v1/chosen.json').read_text(encoding='utf-8'))['params'])
    parent_memory = parent_mod.fit_variant(train_assets, val_contexts, predictor, cfg, parent_params, args.outputs_root / 'parent_fit', args.device, None)
    compat_memory = compat_mod.fit_variant(train_assets, val_contexts, predictor, cfg, compat_params, args.outputs_root / 'compat_fit', args.device, None)

    parent_val_rows = _eval_variant(parent_mod, parent_memory, parent_params, predictor, cfg, val_contexts, int(args.dev_cap), args.device, 'CX34-A (Val)')

    trials = []
    for idx, params_obj in enumerate(mod.param_grid(), start=1):
        fit_dir = args.outputs_root / 'trials' / f'trial_{idx:02d}'
        memory = mod.fit_variant(train_assets, val_contexts, predictor, cfg, params_obj, fit_dir, args.device, None)
        trial_rows = _eval_variant(mod, memory, params_obj, predictor, cfg, val_contexts, int(args.dev_cap), args.device, 'CX45-C (Candidate)')
        success_gain = float(np.mean([float(r['success']) - float(p['success']) for r, p in zip(trial_rows, parent_val_rows)]))
        exp_gain = float(np.mean([float(p['expansions']) - float(r['expansions']) for r, p in zip(trial_rows, parent_val_rows)]))
        time_gain = float(np.mean([float(p['time_ms']) - float(r['time_ms']) for r, p in zip(trial_rows, parent_val_rows)]))
        score = 1_000_000.0 * success_gain + 1_000.0 * exp_gain + float(time_gain)
        trials.append({'params_obj': params_obj, 'memory': memory, 'score': score, 'success_gain': success_gain, 'exp_gain': exp_gain, 'time_gain': time_gain})
        print(f'[cx45c] trial={idx} score={score:.3f} success_gain={success_gain:.6f} exp_gain={exp_gain:.3f} time_gain={time_gain:.3f} params={params_obj}', flush=True)
    chosen = sorted(trials, key=lambda item: item['score'], reverse=True)[0]
    params_obj = chosen['params_obj']
    memory = chosen['memory']

    rows = _eval_cx3(public_contexts, int(args.exp4_cap))
    rows.extend(_eval_variant(parent_mod, parent_memory, parent_params, predictor, cfg, public_contexts, int(args.exp4_cap), args.device, 'CX34-A (Full)'))
    rows.extend(_eval_variant(compat_mod, compat_memory, compat_params, predictor, cfg, public_contexts, int(args.exp4_cap), args.device, 'CX41-B (Full)'))
    rows.extend(_eval_variant(mod, memory, params_obj, predictor, cfg, public_contexts, int(args.exp4_cap), args.device, 'CX45-C (Full)'))
    for spec in mod.ablation_specs():
        rows.extend(_eval_variant(mod, memory, params_obj, predictor, cfg, public_contexts, int(args.exp4_cap), args.device, f"CX45-C ({spec['name']})", ablation=spec))
    _write_csv(args.outputs_root / 'public_case_rows.csv', rows)

    summary = _summary(rows, ('dataset', 'method'))
    delta_vs_cx3 = _delta(summary, ('dataset',), 'CX3-D')
    delta_vs_cx34 = _delta(summary, ('dataset',), 'CX34-A (Full)')
    delta_vs_cx41 = _delta(summary, ('dataset',), 'CX41-B (Full)')
    family_vs_cx34 = _family_delta(rows, 'CX34-A (Full)')
    _write_csv(args.outputs_root / 'public_summary.csv', summary)
    _write_csv(args.outputs_root / 'public_delta_vs_cx3.csv', delta_vs_cx3)
    _write_csv(args.outputs_root / 'public_delta_vs_cx34.csv', delta_vs_cx34)
    _write_csv(args.outputs_root / 'public_delta_vs_cx41.csv', delta_vs_cx41)
    _write_csv(args.outputs_root / 'public_family_delta_vs_cx34.csv', family_vs_cx34)

    std = _standard_audit(mod, memory, params_obj, predictor, args.benchmark_root, int(args.max_mp_cases), int(args.max_csm_cases))
    _write_csv(args.outputs_root / 'standard_field_audit.csv', std)
    (args.outputs_root / 'chosen.json').write_text(json.dumps({'variant': 'CX45-C', 'params': params_obj.__dict__, 'selection_score': float(chosen['score']), 'val_success_gain': float(chosen['success_gain']), 'val_exp_gain': float(chosen['exp_gain']), 'val_time_gain': float(chosen['time_gain'])}, indent=2, ensure_ascii=False), encoding='utf-8')
    write_inputs_sha256([args.ours_checkpoint, args.split_root / 'calib_train.csv', args.split_root / 'calib_val.csv'] + train_files + val_files + public_files, args.outputs_root / 'inputs_sha256.json')

    lines = [
        '# CX45-C Pilot V1',
        '',
        '- protocol: unified public rerun against frozen `CX34-A` and `CX41-B`; macro-bearing evidence-accumulated witness; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit',
        f"- chosen params: `{params_obj.__dict__}`",
        f"- output root: `{args.outputs_root}`",
        '',
        '## Public vs `CX3-D`',
    ]
    for row in delta_vs_cx3:
        lines.append(f"- `{row['method']}`: success_delta_pp=`{float(row['success_delta_pp']):.3f}`, exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`")
    lines += ['', '## Public vs `CX34-A (Full)`']
    for row in delta_vs_cx34:
        lines.append(f"- `{row['method']}`: success_delta_pp=`{float(row['success_delta_pp']):.3f}`, exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`")
    lines += ['', '## Public vs `CX41-B (Full)`']
    for row in delta_vs_cx41:
        lines.append(f"- `{row['method']}`: success_delta_pp=`{float(row['success_delta_pp']):.3f}`, exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`")
    lines += ['', '## Public Family Breakdown vs `CX34-A (Full)`']
    for row in family_vs_cx34:
        lines.append(f"- `{row['scenario']}` / `{row['method']}`: exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`")
    lines += ['', '## Standard Support Audit']
    for row in std:
        lines.append(f"- `{row['dataset']}`: num_cases=`{row['num_cases']}`, max_abs_field_diff=`{float(row['max_abs_field_diff']):.6f}`, mean_abs_field_diff=`{float(row['mean_abs_field_diff']):.6f}`")
    (args.reports_root / 'rs_p0cx45_c_pilot_v1.md').write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    main()
