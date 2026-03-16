from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baselines.common import load_grid_sample
from network.inference import NeuralHeuristicPredictor
from rs_cx.common import CXGlobalConfig, run_standard_astar
from rs_cx8.common import accepted_cx3d_standard, load_nonholonomic_assets, write_inputs_sha256
from rs_cx9 import cx9_a_sbm
from rs_cx9.common import run_hybrid_with_policy


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Locked final evaluation for CX9-A.')
    p.add_argument('--chosen-json', type=Path, default=Path('outputs/rs_p0cx9_a_tuned_pilot_v1/chosen.json'))
    p.add_argument('--hard-benchmark-root', type=Path, default=Path('data/benchmark/rs_root_hard_v2'))
    p.add_argument('--benchmark-root', type=Path, default=Path('data/benchmark'))
    p.add_argument('--split-root', type=Path, default=Path('data/split/calib_hard_v1'))
    p.add_argument('--ours-checkpoint', type=Path, default=Path('outputs/checkpoints/exp3_final_manual_v11b.pt'))
    p.add_argument('--device', type=str, default='cuda')
    p.add_argument('--fixed-cap', type=int, default=20000)
    p.add_argument('--max-mp-cases', type=int, default=800)
    p.add_argument('--max-csm-cases', type=int, default=400)
    p.add_argument('--hard-offset', type=int, default=0)
    p.add_argument('--hard-limit', type=int, default=0)
    p.add_argument('--skip-hard', action='store_true')
    p.add_argument('--skip-standard', action='store_true')
    p.add_argument('--finalize-only', action='store_true')
    p.add_argument('--out-root', type=Path, default=Path('outputs/rs_p0cx9_a_final_eval_v1'))
    p.add_argument('--report-path', type=Path, default=Path('reports/rs_p0cx9_a_final_eval_v1.md'))
    p.add_argument('--paper-table', type=Path, default=Path('paper/tables_rs_root_v1/table_rs_cx9a_final_eval_v1.csv'))
    return p.parse_args()


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames=[]; seen=set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader(); w.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open('r', newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _path_len(plan) -> float:
    arr = np.asarray(plan.path[:, :2], dtype=np.float32) if hasattr(plan, 'path') else np.asarray(plan, dtype=np.float32)
    if arr.shape[0] < 2:
        return float('nan')
    return float(np.sum(np.linalg.norm(arr[1:] - arr[:-1], axis=1)))


def _hard_summary(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    by = defaultdict(list)
    for row in rows:
        by[str(row['method'])].append(row)
    summary_rows = []
    for method, grp in sorted(by.items()):
        summary_rows.append({
            'method': method,
            'num_cases': int(len(grp)),
            'success_rate': float(np.mean([float(r['success']) for r in grp])),
            'avg_expansions': float(np.mean([float(r['expansions']) for r in grp])),
            'avg_time_ms': float(np.mean([float(r['time_ms']) for r in grp])),
            'avg_path_length': float(np.nanmean([float(r['path_length']) for r in grp])) if grp else float('nan'),
        })
    idx = {r['method']: r for r in summary_rows}
    delta_rows = []
    for method in ['Hybrid A* (RS)', 'CX9-A (Full)', 'CX9-A (No-Stability)']:
        if method not in idx or 'CX3-D' not in idx:
            continue
        base = idx['CX3-D']; cur = idx[method]
        delta_rows.append({
            'method': method,
            'baseline': 'CX3-D',
            'success_delta_pp': 100.0 * (float(cur['success_rate']) - float(base['success_rate'])),
            'exp_delta': float(base['avg_expansions']) - float(cur['avg_expansions']),
            'time_delta_ms': float(base['avg_time_ms']) - float(cur['avg_time_ms']),
            'mean_time_overhead_ratio': (float(cur['avg_time_ms']) - float(base['avg_time_ms'])) / max(float(base['avg_time_ms']), 1e-6),
            'path_delta': (float(base['avg_path_length']) - float(cur['avg_path_length'])) if np.isfinite(float(base['avg_path_length'])) and np.isfinite(float(cur['avg_path_length'])) else float('nan'),
        })
    fam_by = defaultdict(list)
    for row in rows:
        fam_by[(str(row['scenario']), str(row['method']))].append(row)
    family_rows = []
    for (scenario, method), grp in sorted(fam_by.items()):
        family_rows.append({
            'scenario': scenario,
            'method': method,
            'num_cases': int(len(grp)),
            'success_rate': float(np.mean([float(r['success']) for r in grp])),
            'avg_expansions': float(np.mean([float(r['expansions']) for r in grp])),
            'avg_time_ms': float(np.mean([float(r['time_ms']) for r in grp])),
            'avg_path_length': float(np.nanmean([float(r['path_length']) for r in grp])) if grp else float('nan'),
        })
    return summary_rows, delta_rows, family_rows


def _standard_summary(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by = defaultdict(list)
    for row in rows:
        by[(str(row['dataset']), str(row['method']))].append(row)
    summary_rows = []
    for (dataset, method), grp in sorted(by.items()):
        summary_rows.append({
            'dataset': dataset,
            'method': method,
            'num_cases': int(len(grp)),
            'success_rate': float(np.mean([float(r['success']) for r in grp])),
            'avg_expansions': float(np.mean([float(r['expansions']) for r in grp])),
            'avg_time_ms': float(np.mean([float(r['time_ms']) for r in grp])),
        })
    idx = {(r['dataset'], r['method']): r for r in summary_rows}
    delta_rows = []
    for dataset in ['mp', 'csm']:
        if (dataset, 'CX3-D') not in idx or (dataset, 'CX9-A (Full)') not in idx:
            continue
        base = idx[(dataset, 'CX3-D')]; cur = idx[(dataset, 'CX9-A (Full)')]
        delta_rows.append({
            'dataset': dataset,
            'method': 'CX9-A (Full)',
            'baseline': 'CX3-D',
            'success_delta_pp': 100.0 * (float(cur['success_rate']) - float(base['success_rate'])),
            'exp_delta': float(base['avg_expansions']) - float(cur['avg_expansions']),
            'time_delta_ms': float(base['avg_time_ms']) - float(cur['avg_time_ms']),
            'mean_time_overhead_ratio': (float(cur['avg_time_ms']) - float(base['avg_time_ms'])) / max(float(base['avg_time_ms']), 1e-6),
        })
    return summary_rows, delta_rows


def _locked_params(chosen_json: Path) -> cx9_a_sbm.CX9ASBMParams:
    data = json.loads(chosen_json.read_text(encoding='utf-8'))
    return cx9_a_sbm.CX9ASBMParams(**data['params'])


def _no_stability(params: cx9_a_sbm.CX9ASBMParams) -> cx9_a_sbm.CX9ASBMParams:
    return cx9_a_sbm.CX9ASBMParams(
        stride_cells=int(params.stride_cells),
        gate_threshold=float(params.gate_threshold),
        neutral_similarity=float(params.neutral_similarity),
        apply_conf_threshold=float(params.apply_conf_threshold),
        local_score_threshold=float(params.local_score_threshold),
        mode_strength=float(params.mode_strength),
        misc_margin=-1.0,
        misc_misc_thr=1.1,
        misc_open_thr=2.0,
        misc_bridge_thr=1.0,
    )


def _read_split_csv(path: Path) -> list[Path]:
    with path.open('r', newline='', encoding='utf-8') as f:
        return [Path(row['path']) for row in csv.DictReader(f)]


def _hard_part_path(out_root: Path, offset: int, limit: int) -> Path:
    tag = f'{offset:04d}_{limit if limit>0 else "all"}'
    return out_root / 'parts' / f'hard_case_rows_{tag}.csv'


def _collect_part_rows(pattern_root: Path, prefix: str) -> list[dict[str, Any]]:
    rows = []
    for path in sorted((pattern_root / 'parts').glob(f'{prefix}_*.csv')):
        rows.extend(_read_csv(path))
    return rows


def _finalize(args: argparse.Namespace, locked: cx9_a_sbm.CX9ASBMParams, no_stability: cx9_a_sbm.CX9ASBMParams) -> None:
    hard_rows = _collect_part_rows(args.out_root, 'hard_case_rows')
    standard_rows = _read_csv(args.out_root / 'parts' / 'standard_case_rows.csv')
    hard_summary, hard_delta, hard_family = _hard_summary(hard_rows)
    _write_csv(args.out_root / 'hard_test_case_rows.csv', hard_rows)
    _write_csv(args.out_root / 'hard_test_summary.csv', hard_summary)
    _write_csv(args.out_root / 'hard_test_delta.csv', hard_delta)
    _write_csv(args.out_root / 'hard_test_family.csv', hard_family)
    standard_summary, standard_delta = _standard_summary(standard_rows)
    _write_csv(args.out_root / 'standard_case_rows.csv', standard_rows)
    _write_csv(args.out_root / 'standard_summary.csv', standard_summary)
    _write_csv(args.out_root / 'standard_delta.csv', standard_delta)

    table_rows = []
    by_method = {r['method']: r for r in hard_summary}
    for method in ['Hybrid A* (RS)', 'CX3-D', 'CX9-A (Full)', 'CX9-A (No-Stability)']:
        if method in by_method:
            r = by_method[method]
            table_rows.append({
                'method': method,
                'hard_success_rate': r['success_rate'],
                'hard_avg_expansions': r['avg_expansions'],
                'hard_avg_time_ms': r['avg_time_ms'],
                'hard_avg_path_length': r['avg_path_length'],
            })
    _write_csv(args.paper_table, table_rows)

    hard_delta_map = {r['method']: r for r in hard_delta}
    fam_summary_map = {(r['scenario'], r['method']): r for r in hard_family}
    fam_delta = defaultdict(dict)
    for scenario in sorted({r['scenario'] for r in hard_family}):
        base = fam_summary_map.get((scenario, 'CX3-D'))
        full = fam_summary_map.get((scenario, 'CX9-A (Full)'))
        ns = fam_summary_map.get((scenario, 'CX9-A (No-Stability)'))
        if base and full:
            fam_delta[scenario]['full_exp_delta'] = float(base['avg_expansions']) - float(full['avg_expansions'])
            fam_delta[scenario]['full_over'] = (float(full['avg_time_ms']) - float(base['avg_time_ms'])) / max(float(base['avg_time_ms']), 1e-6)
        if base and ns:
            fam_delta[scenario]['nostab_exp_delta'] = float(base['avg_expansions']) - float(ns['avg_expansions'])
            fam_delta[scenario]['nostab_over'] = (float(ns['avg_time_ms']) - float(base['avg_time_ms'])) / max(float(base['avg_time_ms']), 1e-6)

    lines = [
        '# P0-CX9-A Final Eval V1',
        '',
        '- protocol: locked final evaluation from tuned chosen params; no post-test retuning',
        f'- chosen json: `{args.chosen_json}`',
        f'- locked params: `{asdict(locked)}`',
        f'- no-stability params: `{asdict(no_stability)}`',
        f'- report table: `{args.paper_table}`',
        f"- inputs sha256: `{args.out_root / 'inputs_sha256.json'}`",
        '',
        '## Hard Benchmark vs accepted `CX3-D`',
    ]
    for method in ['Hybrid A* (RS)', 'CX9-A (Full)', 'CX9-A (No-Stability)']:
        if method in hard_delta_map:
            row = hard_delta_map[method]
            lines.append(f"- `{method}`: success_delta_pp=`{row['success_delta_pp']:.3f}`, exp_delta=`{row['exp_delta']:.3f}`, mean_time_overhead_ratio=`{row['mean_time_overhead_ratio']:.6f}`, path_delta=`{row['path_delta']:.3f}`")
    lines += ['', '## Family Breakdown (Full / No-Stability)']
    for scenario, vals in sorted(fam_delta.items()):
        lines.append(f"- `{scenario}`: full_exp_delta=`{vals.get('full_exp_delta', float('nan')):.3f}`, full_over=`{vals.get('full_over', float('nan')):.6f}`, nostability_exp_delta=`{vals.get('nostab_exp_delta', float('nan')):.3f}`, nostability_over=`{vals.get('nostab_over', float('nan')):.6f}`")
    lines += ['', '## Ordinary Support (`mp/csm`)']
    for row in standard_delta:
        lines.append(f"- `{row['dataset']}`: success_delta_pp=`{row['success_delta_pp']:.3f}`, exp_delta=`{row['exp_delta']:.3f}`, mean_time_overhead_ratio=`{row['mean_time_overhead_ratio']:.6f}`")
    lines += ['', '## Final Verdict']
    full = hard_delta_map.get('CX9-A (Full)')
    passed = False
    if full is not None:
        passed = float(full['exp_delta']) > 0.0 and float(full['mean_time_overhead_ratio']) < 0.30 and float(full['success_delta_pp']) >= 0.0
    if passed:
        lines.append('- `CX9-A` passes the locked final evaluation and is promoted to the new accepted mainline candidate.')
    else:
        lines.append('- `CX9-A` does not hold under locked test evaluation strongly enough for promotion; keep the current accepted mainline.')
    args.report_path.write_text('\n'.join(lines), encoding='utf-8')


def main() -> None:
    args = parse_args()
    args.out_root.mkdir(parents=True, exist_ok=True)
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    locked = _locked_params(args.chosen_json)
    no_stability = _no_stability(locked)

    predictor = NeuralHeuristicPredictor(args.ours_checkpoint, device=args.device, gaussian_sigma=2.5)
    cfg = CXGlobalConfig()
    t0 = time.perf_counter()

    train_files = _read_split_csv(args.split_root / 'calib_train.csv')
    train_assets = load_nonholonomic_assets(train_files, predictor, cfg, int(args.fixed_cap), tag='rs-p0cx9a:hard-train')
    locked_memory = cx9_a_sbm.fit_variant(train_assets, [], predictor, cfg, locked, args.out_root / '_locked_bank', args.device)

    test_files = sorted((args.hard_benchmark_root / 'test').glob('sample_*.npz'))
    if int(args.hard_offset) > 0 or int(args.hard_limit) > 0:
        start = int(args.hard_offset)
        end = None if int(args.hard_limit) <= 0 else start + int(args.hard_limit)
        test_files = test_files[start:end]

    if not args.finalize_only and not args.skip_hard:
        hard_assets = load_nonholonomic_assets(test_files, predictor, cfg, int(args.fixed_cap), tag='rs-p0cx9a:hard-test')
        hard_rows: list[dict[str, Any]] = []
        for i, asset in enumerate(hard_assets, start=1):
            case = asset['case']
            bundle = asset['bundle']
            field = asset['field']
            baseline = asset['baseline_result']
            rs_plan = run_hybrid_with_policy(case, bundle['rs_base'], int(args.fixed_cap), successor_policy=None, record_expanded=False)

            prep_t0 = time.perf_counter()
            full_policy = cx9_a_sbm.make_policy(locked_memory, locked, case, bundle, field, args.device)
            full_prep_ms = (time.perf_counter() - prep_t0) * 1000.0
            full_plan = run_hybrid_with_policy(case, field, int(args.fixed_cap), successor_policy=full_policy, record_expanded=False)

            prep_t0 = time.perf_counter()
            ns_policy = cx9_a_sbm.make_policy(locked_memory, no_stability, case, bundle, field, args.device)
            ns_prep_ms = (time.perf_counter() - prep_t0) * 1000.0
            ns_plan = run_hybrid_with_policy(case, field, int(args.fixed_cap), successor_policy=ns_policy, record_expanded=False)

            for method, plan, prep_ms in [
                ('Hybrid A* (RS)', rs_plan, 0.0),
                ('CX3-D', baseline, 0.0),
                ('CX9-A (Full)', full_plan, full_prep_ms),
                ('CX9-A (No-Stability)', ns_plan, ns_prep_ms),
            ]:
                hard_rows.append({
                    'sample_name': asset['path'].name,
                    'scenario': str(case['scenario']),
                    'source': str(asset['path']),
                    'method': method,
                    'success': float(plan.success if hasattr(plan, 'success') else plan['success']),
                    'expansions': float(plan.expansions if hasattr(plan, 'expansions') else plan['expansions']),
                    'time_ms': float((plan.runtime_ms if hasattr(plan, 'runtime_ms') else plan['runtime_ms']) + prep_ms),
                    'prep_time_ms': float(prep_ms),
                    'path_length': _path_len(plan if hasattr(plan, 'path') else np.asarray(plan['path'], dtype=np.float32)),
                })
            if i % 5 == 0 or i == len(hard_assets):
                print(f'[rs-p0cx9a:hard-test] {i}/{len(hard_assets)}')
        _write_csv(_hard_part_path(args.out_root, int(args.hard_offset), int(args.hard_limit)), hard_rows)

    if not args.finalize_only and not args.skip_standard:
        standard_rows: list[dict[str, Any]] = []
        for dataset, limit in [('mp', int(args.max_mp_cases)), ('csm', int(args.max_csm_cases))]:
            files = sorted((args.benchmark_root / dataset / 'test').glob('sample_*.npz'))[:limit]
            for i, path in enumerate(files, start=1):
                sample = load_grid_sample(path)
                _, base_field = accepted_cx3d_standard(sample, predictor)
                base = run_standard_astar(sample, base_field, 50000)
                cx_field = cx9_a_sbm.build_standard_field(sample, predictor, locked)
                cx = run_standard_astar(sample, cx_field, 50000)
                for method, result in [('CX3-D', base), ('CX9-A (Full)', cx)]:
                    standard_rows.append({
                        'dataset': dataset,
                        'sample_name': path.name,
                        'method': method,
                        'success': float(result['success']),
                        'expansions': float(result['expansions']),
                        'time_ms': float(result['runtime_ms']),
                    })
                if i % 100 == 0 or i == len(files):
                    print(f'[rs-p0cx9a:standard] {dataset} {i}/{len(files)}')
        std_path = args.out_root / 'parts' / 'standard_case_rows.csv'
        existing = _read_csv(std_path)
        merged = {(r['dataset'], r['sample_name'], r['method']): r for r in existing}
        for r in standard_rows:
            merged[(r['dataset'], r['sample_name'], r['method'])] = r
        _write_csv(std_path, list(merged.values()))

    inputs = [args.chosen_json, args.ours_checkpoint, args.hard_benchmark_root / 'meta.json', args.hard_benchmark_root / 'test_index.csv', args.split_root / 'calib_train.csv'] + train_files + sorted((args.hard_benchmark_root / 'test').glob('sample_*.npz'))
    write_inputs_sha256(inputs, args.out_root / 'inputs_sha256.json')
    manifest = {
        'version': 'rs_p0cx9_a_final_eval_v1',
        'runtime_hours': float((time.perf_counter() - t0) / 3600.0),
        'chosen_json': str(args.chosen_json),
        'locked_params': asdict(locked),
        'no_stability_params': asdict(no_stability),
        'inputs_sha256': json.loads((args.out_root / 'inputs_sha256.json').read_text(encoding='utf-8')),
    }
    (args.out_root / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    _finalize(args, locked, no_stability)


if __name__ == '__main__':
    main()
