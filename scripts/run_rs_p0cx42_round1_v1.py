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
from rs_cx24.common import build_frozen_haa_teacher
from rs_cx8.common import load_nonholonomic_assets, load_nonholonomic_contexts, write_inputs_sha256

MODULES = {'CX42-A': 'rs_cx42.cx42_a_dcl'}
SLUG = {'CX42-A': 'a'}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Run P0-CX42 round1 pilots.')
    p.add_argument('--variants', type=str, default='CX42-A')
    p.add_argument('--split-root', type=Path, default=Path('data/split/calib_hard_v1'))
    p.add_argument('--parasol-root', type=Path, default=Path('data/benchmark/parasol_narrow/test'))
    p.add_argument('--benchmark-root', type=Path, default=Path('data/benchmark'))
    p.add_argument('--ours-checkpoint', type=Path, default=Path('outputs/checkpoints/exp3_final_manual_v11b.pt'))
    p.add_argument('--device', type=str, default='cuda')
    p.add_argument('--dev-cap', type=int, default=20000)
    p.add_argument('--exp4-cap', type=int, default=20000)
    p.add_argument('--max-mp-cases', type=int, default=800)
    p.add_argument('--max-csm-cases', type=int, default=400)
    p.add_argument('--reports-root', type=Path, default=Path('reports'))
    p.add_argument('--outputs-root', type=Path, default=Path('outputs'))
    return p.parse_args()


def _variants(raw: str) -> list[str]:
    return [item.strip() for item in str(raw).split(',') if item.strip()]


def _read_split_rows(path: Path) -> list[dict[str, Any]]:
    with path.open('r', newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
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


def _family_delta(rows: list[dict[str, Any]], extra_keys: tuple[str, ...], baseline_method: str) -> list[dict[str, Any]]:
    return _delta(_summary(rows, extra_keys + ('scenario', 'method')), extra_keys + ('scenario',), baseline_method)


def _eval_variant(mod, memory, params_obj, predictor, cfg, assets, cap, device, method_name, *, ablation=None):
    rows = []
    total = len(assets)
    for idx, asset in enumerate(assets, start=1):
        field = mod.build_nonholonomic_field(asset['case'], predictor, cfg, params_obj, memory)
        bundle = asset['case'].get('_cx21_bundle', asset['bundle'])
        prep_t0 = time.perf_counter()
        policy = mod.make_policy(memory, params_obj, asset['case'], bundle, field, device, ablation=ablation)
        prep_ms = (time.perf_counter() - prep_t0) * 1000.0
        plan = run_hybrid_with_policy(asset['case'], field, int(cap), successor_policy=policy, record_expanded=False)
        rows.append({'sample_name': str(asset['path'].name), 'scenario': str(asset['case']['scenario']), 'method': method_name, 'success': float(plan.success), 'expansions': float(plan.expansions), 'time_ms': float(plan.runtime_ms + prep_ms)})
        if idx % 5 == 0 or idx == total:
            print(f'[{method_name}] {idx}/{total}', flush=True)
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
                print(f'[cx42:standard:{dataset}] {idx}/{len(files)}', flush=True)
        rows.append({'dataset': dataset, 'num_cases': int(len(files)), 'max_abs_field_diff': float(max(diffs) if diffs else 0.0), 'mean_abs_field_diff': float(np.mean(diffs) if diffs else 0.0)})
    return rows


def main():
    args = parse_args()
    args.reports_root.mkdir(parents=True, exist_ok=True)
    args.outputs_root.mkdir(parents=True, exist_ok=True)
    variants = _variants(args.variants)
    predictor = NeuralHeuristicPredictor(args.ours_checkpoint, device=args.device, gaussian_sigma=2.5)
    cfg = CXGlobalConfig()
    train_rows = _read_split_rows(args.split_root / 'calib_train.csv')
    val_rows = _read_split_rows(args.split_root / 'calib_val.csv')
    train_files = [Path(r['path']) for r in train_rows]
    val_files = [Path(r['path']) for r in val_rows]
    public_files = sorted(args.parasol_root.glob('sample_*.npz'))
    train_assets = load_nonholonomic_assets(train_files, predictor, cfg, int(args.dev_cap), tag='cx42:calib-train')
    val_contexts = load_nonholonomic_contexts(val_files, predictor, cfg, tag='cx42:calib-val')
    public_contexts = load_nonholonomic_contexts(public_files, predictor, cfg, tag='cx42:public')
    haa_teacher = build_frozen_haa_teacher(train_assets, val_contexts, predictor, cfg, args.device, args.outputs_root / 'rs_p0cx42_haa_cache')
    dependencies = {'haa_teacher': haa_teacher}

    parent_mod = importlib.import_module('rs_cx34.cx34_a_msr')
    parent_params = parent_mod.CX34AMSRParams(**json.loads(Path('outputs/rs_p0cx34_a_pilot_v1/chosen.json').read_text())['params'])
    parent_val_rows = _eval_variant(parent_mod, {'haa_teacher': haa_teacher}, parent_params, predictor, cfg, val_contexts, int(args.dev_cap), args.device, 'CX34-A (Parent)')
    parent_val_map = {str(r['sample_name']): dict(r) for r in parent_val_rows}
    parent_public_rows = [r for r in _read_csv(Path('outputs/rs_p0cx34_a_pilot_v1/public_case_rows.csv')) if str(r.get('method')) == 'CX34-A (Full)' and str(r.get('dataset')) == 'exp4']
    cx3_public_rows = [r for r in _read_csv(Path('outputs/rs_p0cx34_a_pilot_v1/public_case_rows.csv')) if str(r.get('method')) == 'CX3-D' and str(r.get('dataset')) == 'exp4']

    summary_rows = []
    standard_rows_all = []
    for variant in variants:
        mod = importlib.import_module(MODULES[variant]); slug = SLUG[variant]
        out_root = args.outputs_root / f'rs_p0cx42_{slug}_pilot_v1'; out_root.mkdir(parents=True, exist_ok=True)
        report_path = args.reports_root / f'rs_p0cx42_{slug}_pilot_v1.md'
        trials = []
        for idx, params_obj in enumerate(mod.param_grid(), start=1):
            fit_dir = out_root / 'trials' / f'trial_{idx:02d}'
            memory = mod.fit_variant(train_assets, val_contexts, predictor, cfg, params_obj, fit_dir, args.device, dependencies)
            trial_rows = _eval_variant(mod, memory, params_obj, predictor, cfg, val_contexts, int(args.dev_cap), args.device, f'{variant} (Candidate)')
            score = float(np.mean([float(parent_val_map[str(r['sample_name'])]['expansions']) - float(r['expansions']) for r in trial_rows])) if trial_rows else 0.0
            trials.append({'params_obj': params_obj, 'memory': memory, 'score': score})
            print(f'[cx42:{variant}] trial={idx} params={params_obj} score={score}', flush=True)
        chosen = sorted(trials, key=lambda x: x['score'], reverse=True)[0]
        params_obj = chosen['params_obj']; memory = chosen['memory']
        public_rows = []; public_rows.extend(cx3_public_rows); public_rows.extend(parent_public_rows)
        variant_rows = _eval_variant(mod, memory, params_obj, predictor, cfg, public_contexts, int(args.exp4_cap), args.device, f'{variant} (Full)')
        for row in variant_rows: row['dataset'] = 'exp4'
        public_rows.extend(variant_rows)
        for spec in getattr(mod, 'ablation_specs', lambda: [])():
            ab_rows = _eval_variant(mod, memory, params_obj, predictor, cfg, public_contexts, int(args.exp4_cap), args.device, f"{variant} ({spec['name']})", ablation=spec)
            for row in ab_rows: row['dataset'] = 'exp4'
            public_rows.extend(ab_rows)
        _write_csv(out_root / 'public_case_rows.csv', public_rows)
        s = _summary(public_rows, ('dataset', 'method'))
        d1 = _delta(s, ('dataset',), 'CX3-D')
        d2 = _delta(s, ('dataset',), 'CX34-A (Full)')
        f1 = _family_delta(public_rows, ('dataset',), 'CX3-D')
        f2 = _family_delta(public_rows, ('dataset',), 'CX34-A (Full)')
        _write_csv(out_root / 'public_summary.csv', s)
        _write_csv(out_root / 'public_delta_vs_cx3.csv', d1)
        _write_csv(out_root / 'public_delta_vs_parent.csv', d2)
        _write_csv(out_root / 'public_family_delta_vs_cx3.csv', f1)
        _write_csv(out_root / 'public_family_delta_vs_parent.csv', f2)
        std = _standard_audit(mod, memory, params_obj, predictor, args.benchmark_root, int(args.max_mp_cases), int(args.max_csm_cases))
        _write_csv(out_root / 'standard_field_audit.csv', std)
        for row in std: standard_rows_all.append({'variant': variant, **row})
        chosen_json = {'variant': variant, 'params': params_obj.__dict__, 'out_root': str(out_root)}
        (out_root / 'chosen.json').write_text(json.dumps(chosen_json, indent=2, ensure_ascii=False), encoding='utf-8')
        inputs = [args.ours_checkpoint, args.split_root / 'calib_train.csv', args.split_root / 'calib_val.csv'] + train_files + val_files + public_files
        write_inputs_sha256(inputs, out_root / 'inputs_sha256.json')

        lines = [f'# {variant} Pilot V1', '', '- protocol: frozen `CX34-A / Subtype-Specific Macro Rescue` parent; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit', f"- chosen params: `{params_obj.__dict__}`", f"- output root: `{out_root}`", '', '## Public vs `CX3-D`']
        for row in d1: lines.append(f"- `{row['method']}`: success_delta_pp=`{float(row['success_delta_pp']):.3f}`, exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`")
        lines += ['', '## Public Family Breakdown vs `CX3-D`']
        for row in f1: lines.append(f"- `{row['scenario']}` / `{row['method']}`: exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`")
        lines += ['', '## Public vs `CX34-A (Full)`']
        for row in d2: lines.append(f"- `{row['method']}`: success_delta_pp=`{float(row['success_delta_pp']):.3f}`, exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`")
        lines += ['', '## Public Family Breakdown vs `CX34-A (Full)`']
        for row in f2: lines.append(f"- `{row['scenario']}` / `{row['method']}`: exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`")
        lines += ['', '## Standard Support Audit']
        for row in std: lines.append(f"- `{row['dataset']}`: num_cases=`{row['num_cases']}`, max_abs_field_diff=`{float(row['max_abs_field_diff']):.6f}`, mean_abs_field_diff=`{float(row['mean_abs_field_diff']):.6f}`")
        report_path.write_text('\n'.join(lines), encoding='utf-8')
        full1 = next(r for r in d1 if r['method'] == f'{variant} (Full)')
        full2 = next(r for r in d2 if r['method'] == f'{variant} (Full)')
        misc = next(r for r in f2 if r['method'] == f'{variant} (Full)' and r['scenario'] == 'parasol_misc')
        maze = next(r for r in f2 if r['method'] == f'{variant} (Full)' and r['scenario'] == 'maze')
        flange = next(r for r in f2 if r['method'] == f'{variant} (Full)' and r['scenario'] == 'flange')
        narrow = next(r for r in f2 if r['method'] == f'{variant} (Full)' and r['scenario'] == 'narrow_passage')
        summary_rows.append({'variant': variant, 'chosen_params': params_obj.__dict__, 'exp4_exp_delta_vs_cx3': float(full1['exp_delta']), 'exp4_overhead_vs_cx3': float(full1['mean_time_overhead_ratio']), 'exp4_exp_delta_vs_parent': float(full2['exp_delta']), 'misc_delta_vs_parent': float(misc['exp_delta']), 'maze_delta_vs_parent': float(maze['exp_delta']), 'flange_delta_vs_parent': float(flange['exp_delta']), 'narrow_delta_vs_parent': float(narrow['exp_delta']), 'report_path': str(report_path), 'out_root': str(out_root)})

    summary_root = args.outputs_root / 'rs_p0cx42_round1_summary'; summary_root.mkdir(parents=True, exist_ok=True)
    _write_csv(summary_root / 'summary.csv', summary_rows)
    (summary_root / 'summary.json').write_text(json.dumps({'variants': summary_rows}, indent=2, ensure_ascii=False), encoding='utf-8')
    lines = ['# P0-CX42 Round1 Summary', '', '- protocol: frozen `CX34-A` parent; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit', '', '## Variant Readout']
    for row in summary_rows: lines.append(f"- `{row['variant']}`: exp4 vs `CX3-D` exp_delta=`{row['exp4_exp_delta_vs_cx3']:.3f}`, overhead=`{row['exp4_overhead_vs_cx3']:.6f}`, vs parent exp_delta=`{row['exp4_exp_delta_vs_parent']:.3f}`, misc=`{row['misc_delta_vs_parent']:.3f}`, maze=`{row['maze_delta_vs_parent']:.3f}`, flange=`{row['flange_delta_vs_parent']:.3f}`, narrow=`{row['narrow_delta_vs_parent']:.3f}`")
    (args.reports_root / 'rs_p0cx42_round1_summary.md').write_text('\n'.join(lines), encoding='utf-8')
    audit_lines = ['# P0-CX42 Standard Audit V1', '', '- protocol: ordinary-support audit checks `build_standard_field == accepted CX3-D` by construction', '']
    for row in standard_rows_all: audit_lines.append(f"- `{row['variant']}` / `{row['dataset']}`: num_cases=`{row['num_cases']}`, max_abs_field_diff=`{float(row['max_abs_field_diff']):.6f}`, mean_abs_field_diff=`{float(row['mean_abs_field_diff']):.6f}`")
    (args.reports_root / 'rs_p0cx42_standard_audit_v1.md').write_text('\n'.join(audit_lines), encoding='utf-8')


if __name__ == '__main__':
    main()
