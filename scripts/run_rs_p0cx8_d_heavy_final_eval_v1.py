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

from network.inference import NeuralHeuristicPredictor
from rs_cx.common import CXGlobalConfig
from rs_cx8.common import load_nonholonomic_assets, run_hybrid_with_policy, write_inputs_sha256
from rs_cx8 import cx8_d_heavy


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Locked final evaluation for CX8-D heavy.')
    p.add_argument('--chosen-json', type=Path, default=Path('outputs/rs_p0cx8_d_hard_pilot_v1/chosen.json'))
    p.add_argument('--hard-benchmark-root', type=Path, default=Path('data/benchmark/rs_root_hard_v2'))
    p.add_argument('--ours-checkpoint', type=Path, default=Path('outputs/checkpoints/exp3_final_manual_v11b.pt'))
    p.add_argument('--device', type=str, default='cuda')
    p.add_argument('--fixed-cap', type=int, default=20000)
    p.add_argument('--hard-offset', type=int, default=0)
    p.add_argument('--hard-limit', type=int, default=0)
    p.add_argument('--finalize-only', action='store_true')
    p.add_argument('--out-root', type=Path, default=Path('outputs/rs_p0cx8_d_heavy_final_eval_v1'))
    p.add_argument('--report-path', type=Path, default=Path('reports/rs_p0cx8_d_heavy_final_eval_v1.md'))
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


def _summary(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
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
    for method in ['Hybrid A* (RS)', 'CX8-D (Heavy)']:
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


def _part_path(out_root: Path, offset: int, limit: int) -> Path:
    tag = f'{offset:04d}_{limit if limit>0 else "all"}'
    return out_root / 'parts' / f'hard_case_rows_{tag}.csv'


def _collect_parts(out_root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted((out_root / 'parts').glob('hard_case_rows_*.csv')):
        rows.extend(_read_csv(path))
    return rows


def _finalize(args: argparse.Namespace, locked_params: cx8_d_heavy.CX8DHeavyParams, chosen: dict[str, Any]) -> None:
    rows = _collect_parts(args.out_root)
    summary_rows, delta_rows, family_rows = _summary(rows)
    _write_csv(args.out_root / 'hard_test_case_rows.csv', rows)
    _write_csv(args.out_root / 'hard_test_summary.csv', summary_rows)
    _write_csv(args.out_root / 'hard_test_delta.csv', delta_rows)
    _write_csv(args.out_root / 'hard_test_family.csv', family_rows)

    cx9_ref = None
    ref_path = Path('outputs/rs_p0cx9_a_final_eval_v1/hard_test_delta.csv')
    if ref_path.exists():
        for row in _read_csv(ref_path):
            if row['method'] == 'CX9-A (Full)':
                cx9_ref = row
                break

    fam_map = {(r['scenario'], r['method']): r for r in family_rows}
    fam_delta = defaultdict(dict)
    for scenario in sorted({r['scenario'] for r in family_rows}):
        base = fam_map.get((scenario, 'CX3-D'))
        heavy = fam_map.get((scenario, 'CX8-D (Heavy)'))
        if base and heavy:
            fam_delta[scenario]['exp_delta'] = float(base['avg_expansions']) - float(heavy['avg_expansions'])
            fam_delta[scenario]['over'] = (float(heavy['avg_time_ms']) - float(base['avg_time_ms'])) / max(float(base['avg_time_ms']), 1e-6)
            fam_delta[scenario]['success_delta_pp'] = 100.0 * (float(heavy['success_rate']) - float(base['success_rate']))

    lines = [
        '# P0-CX8-D Heavy Final Eval V1',
        '',
        '- protocol: locked heavy retrospective evaluation; no post-test retuning',
        f'- chosen json: `{args.chosen_json}`',
        f'- locked heavy params: `{asdict(locked_params)}`',
        f"- inputs sha256: `{args.out_root / 'inputs_sha256.json'}`",
        '',
        '## Hard Benchmark vs accepted `CX3-D`',
    ]
    delta_map = {r['method']: r for r in delta_rows}
    for method in ['Hybrid A* (RS)', 'CX8-D (Heavy)']:
        if method in delta_map:
            row = delta_map[method]
            lines.append(f"- `{method}`: success_delta_pp=`{row['success_delta_pp']:.3f}`, exp_delta=`{row['exp_delta']:.3f}`, mean_time_overhead_ratio=`{row['mean_time_overhead_ratio']:.6f}`, path_delta=`{row['path_delta']:.3f}`")
    if cx9_ref is not None:
        lines += ['', '## Reference vs `CX9-A` Final Eval']
        lines.append(f"- `CX9-A (Full)` final-eval reference: success_delta_pp=`{float(cx9_ref['success_delta_pp']):.3f}`, exp_delta=`{float(cx9_ref['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(cx9_ref['mean_time_overhead_ratio']):.6f}`")
    lines += ['', '## Family Breakdown (Heavy vs `CX3-D`)']
    for scenario, vals in sorted(fam_delta.items()):
        lines.append(f"- `{scenario}`: success_delta_pp=`{vals.get('success_delta_pp', float('nan')):.3f}`, exp_delta=`{vals.get('exp_delta', float('nan')):.3f}`, mean_time_overhead_ratio=`{vals.get('over', float('nan')):.6f}`")
    lines += ['', '## Ceiling Reading']
    heavy = delta_map.get('CX8-D (Heavy)')
    if heavy is not None and float(heavy['exp_delta']) > 0.0:
        lines.append('- `CX8-D Heavy` generalizes positively on test, which means the ceiling of semantic intervention remains real but computationally expensive.')
    else:
        lines.append('- `CX8-D Heavy` does not retain a positive test-side expansion gain, so the strongest dev-side semantic signal does not generalize to the locked hard benchmark.')
    lines += ['', '## Final Verdict']
    lines.append('- This evaluation is ceiling-oriented only and does not override the accepted mainline by itself.')
    args.report_path.write_text('\n'.join(lines), encoding='utf-8')


def main() -> None:
    args = parse_args()
    args.out_root.mkdir(parents=True, exist_ok=True)
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    predictor = NeuralHeuristicPredictor(args.ours_checkpoint, device=args.device, gaussian_sigma=2.5)
    cfg = CXGlobalConfig()
    t0 = time.perf_counter()

    locked_memory = cx8_d_heavy.load_locked_memory(args.chosen_json, args.device)
    locked_params = locked_memory['params']
    chosen = locked_memory['chosen']

    if not args.finalize_only:
        test_files = sorted((args.hard_benchmark_root / 'test').glob('sample_*.npz'))
        if int(args.hard_offset) > 0 or int(args.hard_limit) > 0:
            start = int(args.hard_offset)
            end = None if int(args.hard_limit) <= 0 else start + int(args.hard_limit)
            test_files = test_files[start:end]
        hard_assets = load_nonholonomic_assets(test_files, predictor, cfg, int(args.fixed_cap), tag='rs-p0cx8d-heavy:test')
        rows = []
        for i, asset in enumerate(hard_assets, start=1):
            case = asset['case']; bundle = asset['bundle']; field = asset['field']
            baseline = asset['baseline_result']
            rs_plan = run_hybrid_with_policy(case, bundle['rs_base'], int(args.fixed_cap), successor_policy=None, record_expanded=False)
            prep_t0 = time.perf_counter()
            policy = cx8_d_heavy.make_policy_from_locked(locked_memory, case, bundle, field, args.device)
            prep_ms = (time.perf_counter() - prep_t0) * 1000.0
            heavy_plan = run_hybrid_with_policy(case, field, int(args.fixed_cap), successor_policy=policy, record_expanded=False)
            for method, plan, extra_ms in [
                ('Hybrid A* (RS)', rs_plan, 0.0),
                ('CX3-D', baseline, 0.0),
                ('CX8-D (Heavy)', heavy_plan, prep_ms),
            ]:
                rows.append({
                    'sample_name': asset['path'].name,
                    'scenario': str(case['scenario']),
                    'source': str(asset['path']),
                    'method': method,
                    'success': float(plan.success if hasattr(plan, 'success') else plan['success']),
                    'expansions': float(plan.expansions if hasattr(plan, 'expansions') else plan['expansions']),
                    'time_ms': float((plan.runtime_ms if hasattr(plan, 'runtime_ms') else plan['runtime_ms']) + extra_ms),
                    'prep_time_ms': float(extra_ms),
                    'path_length': _path_len(plan if hasattr(plan, 'path') else np.asarray(plan['path'], dtype=np.float32)),
                })
            if i % 5 == 0 or i == len(hard_assets):
                print(f'[rs-p0cx8d-heavy:test] {i}/{len(hard_assets)}')
        _write_csv(_part_path(args.out_root, int(args.hard_offset), int(args.hard_limit)), rows)

    inputs = [args.chosen_json, args.ours_checkpoint, args.hard_benchmark_root / 'meta.json', args.hard_benchmark_root / 'test_index.csv'] + sorted((args.hard_benchmark_root / 'test').glob('sample_*.npz'))
    write_inputs_sha256(inputs, args.out_root / 'inputs_sha256.json')
    manifest = {
        'version': 'rs_p0cx8_d_heavy_final_eval_v1',
        'runtime_hours': float((time.perf_counter() - t0) / 3600.0),
        'chosen_json': str(args.chosen_json),
        'locked_params': asdict(locked_params),
        'inputs_sha256': json.loads((args.out_root / 'inputs_sha256.json').read_text(encoding='utf-8')),
    }
    (args.out_root / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    _finalize(args, locked_params, chosen)


if __name__ == '__main__':
    main()
