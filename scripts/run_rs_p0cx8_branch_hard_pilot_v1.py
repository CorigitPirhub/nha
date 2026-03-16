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

from network.inference import NeuralHeuristicPredictor
from rs_cx.common import CXGlobalConfig
from rs_cx8.common import load_nonholonomic_assets, run_hybrid_with_policy, write_inputs_sha256

MODULES = {
    'CX8-A': 'rs_cx8.cx8_a_app',
    'CX8-D': 'rs_cx8.cx8_d_bca',
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Run branch-specific P0-CX8 hard-family dev-only pilot.')
    p.add_argument('--variant', type=str, required=True, choices=sorted(MODULES.keys()))
    p.add_argument('--split-root', type=Path, default=Path('data/split/calib_hard_v1'))
    p.add_argument('--ours-checkpoint', type=Path, default=Path('outputs/checkpoints/exp3_final_manual_v11b.pt'))
    p.add_argument('--device', type=str, default='cuda')
    p.add_argument('--fixed-cap', type=int, default=20000)
    p.add_argument('--out-root', type=Path, required=True)
    p.add_argument('--report-path', type=Path, required=True)
    return p.parse_args()


def _read_split_csv(path: Path) -> list[Path]:
    with path.open('r', newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    return [Path(row['path']) for row in rows]


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader(); writer.writerows(rows)


def _path_len(plan) -> float:
    if plan.path.size <= 0:
        return float('nan')
    arr = np.asarray(plan.path[:, :2], dtype=np.float32)
    if arr.shape[0] < 2:
        return float('nan')
    return float(np.sum(np.linalg.norm(arr[1:] - arr[:-1], axis=1)))


def _choose_trial(trials: list[dict[str, Any]]) -> dict[str, Any]:
    feasible = [t for t in trials if float(t['val_summary']['time_overhead_ratio']) <= 0.10]
    ranked = feasible if feasible else trials
    ranked.sort(
        key=lambda t: (
            float(t['val_summary']['success_delta_pp']),
            float(t['val_summary']['exp_delta']),
            -float(t['val_summary']['time_overhead_ratio']),
            float(t['val_summary']['path_delta']) if np.isfinite(float(t['val_summary']['path_delta'])) else 0.0,
        ),
        reverse=True,
    )
    return ranked[0]


def main() -> None:
    args = parse_args()
    args.out_root.mkdir(parents=True, exist_ok=True)
    args.report_path.parent.mkdir(parents=True, exist_ok=True)

    train_files = _read_split_csv(args.split_root / 'calib_train.csv')
    val_files = _read_split_csv(args.split_root / 'calib_val.csv')

    predictor = NeuralHeuristicPredictor(args.ours_checkpoint, device=args.device, gaussian_sigma=2.5)
    cfg = CXGlobalConfig()
    t0 = time.perf_counter()
    train_assets = load_nonholonomic_assets(train_files, predictor, cfg, int(args.fixed_cap), tag=f'rs-p0cx8-{args.variant.lower()}:train')
    val_assets = load_nonholonomic_assets(val_files, predictor, cfg, int(args.fixed_cap), tag=f'rs-p0cx8-{args.variant.lower()}:val')

    mod = importlib.import_module(MODULES[args.variant])
    trials = []
    trial_root = args.out_root / 'trials'
    for idx, params_obj in enumerate(mod.param_grid(), start=1):
        fit_dir = trial_root / f'trial_{idx:02d}'
        memory = mod.fit_variant(train_assets, val_assets, predictor, cfg, params_obj, fit_dir, args.device)
        case_rows = []
        for asset in val_assets:
            baseline = asset['baseline_result']
            policy = mod.make_policy(memory, params_obj, asset['case'], asset['bundle'], asset['field'], args.device)
            plan = run_hybrid_with_policy(asset['case'], asset['field'], int(args.fixed_cap), successor_policy=policy, record_expanded=False)
            case_rows.append({
                'sample_name': asset['path'].name,
                'scenario': str(asset['case']['scenario']),
                'baseline_success': float(baseline.success),
                'baseline_expansions': float(baseline.expansions),
                'baseline_time_ms': float(baseline.runtime_ms),
                'baseline_path_length': _path_len(baseline),
                'cx_success': float(plan.success),
                'cx_expansions': float(plan.expansions),
                'cx_time_ms': float(plan.runtime_ms),
                'cx_path_length': _path_len(plan),
                'success_delta': float(plan.success) - float(baseline.success),
                'exp_delta': float(baseline.expansions) - float(plan.expansions),
                'time_delta_ms': float(baseline.runtime_ms) - float(plan.runtime_ms),
                'time_overhead_ratio': (float(plan.runtime_ms) - float(baseline.runtime_ms)) / max(float(baseline.runtime_ms), 1e-6),
                'path_delta': (float(_path_len(baseline)) - float(_path_len(plan))) if np.isfinite(float(_path_len(baseline))) and np.isfinite(float(_path_len(plan))) else float('nan'),
            })
        val_summary = {
            'success_delta_pp': 100.0 * float(np.mean([r['success_delta'] for r in case_rows])) if case_rows else 0.0,
            'exp_delta': float(np.mean([r['exp_delta'] for r in case_rows])) if case_rows else 0.0,
            'time_delta_ms': float(np.mean([r['time_delta_ms'] for r in case_rows])) if case_rows else 0.0,
            'time_overhead_ratio': float(np.mean([r['time_overhead_ratio'] for r in case_rows])) if case_rows else 0.0,
            'path_delta': float(np.nanmean([r['path_delta'] for r in case_rows])) if case_rows else float('nan'),
        }
        trials.append({'params_obj': params_obj, 'memory': memory, 'fit_dir': fit_dir, 'case_rows': case_rows, 'val_summary': val_summary})
        print(f'[rs-p0cx8-{args.variant.lower()}] trial={idx} params={params_obj} summary={val_summary}')

    chosen = _choose_trial(trials)
    chosen_json = {
        'variant': args.variant,
        'params': chosen['params_obj'].__dict__,
        'val_summary': chosen['val_summary'],
        'fit_dir': str(chosen['fit_dir']),
        'best_val_loss': float(chosen['memory'].get('best_val_loss', float('nan'))),
        'train_samples': int(chosen['memory'].get('train_samples', 0)),
        'val_samples': int(chosen['memory'].get('val_samples', 0)),
    }
    (args.out_root / 'chosen.json').write_text(json.dumps(chosen_json, indent=2, ensure_ascii=False), encoding='utf-8')

    chosen_rows = chosen['case_rows']
    _write_csv(args.out_root / 'calib_val_case_rows.csv', chosen_rows)
    family_rows = []
    by = defaultdict(list)
    for row in chosen_rows:
        by[str(row['scenario'])].append(row)
    for fam, grp in sorted(by.items()):
        family_rows.append({
            'scenario': fam,
            'num_cases': len(grp),
            'success_delta_pp': 100.0 * float(np.mean([r['success_delta'] for r in grp])),
            'exp_delta': float(np.mean([r['exp_delta'] for r in grp])),
            'time_overhead_ratio': float(np.mean([r['time_overhead_ratio'] for r in grp])),
        })
    _write_csv(args.out_root / 'calib_val_family_rows.csv', family_rows)

    inputs = [args.ours_checkpoint, args.split_root / 'manifest.json', args.split_root / 'calib_train.csv', args.split_root / 'calib_val.csv'] + train_files + val_files
    write_inputs_sha256(inputs, args.out_root / 'inputs_sha256.json')
    manifest = {
        'version': 'rs_p0cx8_branch_hard_pilot_v1',
        'variant': args.variant,
        'runtime_hours': float((time.perf_counter() - t0) / 3600.0),
        'split_root': str(args.split_root),
        'fixed_cap': int(args.fixed_cap),
        'chosen': chosen_json,
        'inputs_sha256': json.loads((args.out_root / 'inputs_sha256.json').read_text(encoding='utf-8')),
    }
    (args.out_root / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')

    lines = [
        f'# {args.variant} Hard Pilot V1',
        '',
        '- scope: `calib_hard_v1` dev-only pilot; no test data used',
        f'- branch: `{args.variant}`',
        f'- split root: `{args.split_root}`',
        f'- train cases: `{len(train_files)}`',
        f'- val cases: `{len(val_files)}`',
        f'- cap: `{int(args.fixed_cap)}`',
        f"- chosen params: `{chosen_json['params']}`",
        f"- train/val samples: `{chosen_json['train_samples']}`/`{chosen_json['val_samples']}`",
        f"- inputs sha256: `{args.out_root / 'inputs_sha256.json'}`",
        '',
        '## Overall vs accepted `CX3-D` on calib_val',
        f"- success_delta_pp=`{chosen_json['val_summary']['success_delta_pp']:.3f}`",
        f"- exp_delta=`{chosen_json['val_summary']['exp_delta']:.3f}`",
        f"- time_delta_ms=`{chosen_json['val_summary']['time_delta_ms']:.3f}`",
        f"- mean_time_overhead_ratio=`{chosen_json['val_summary']['time_overhead_ratio']:.6f}`",
        f"- path_delta=`{chosen_json['val_summary']['path_delta']:.3f}`",
        '',
        '## Family Breakdown',
    ]
    for row in family_rows:
        lines.append(f"- `{row['scenario']}`: success_delta_pp=`{row['success_delta_pp']:.3f}`, exp_delta=`{row['exp_delta']:.3f}`, time_overhead_ratio=`{row['time_overhead_ratio']:.6f}`")
    lines += ['', '## Readout']
    if float(chosen_json['val_summary']['exp_delta']) > 0.0 and float(chosen_json['val_summary']['time_overhead_ratio']) <= 0.10:
        lines.append('- result: positive hard-family pilot trend with controlled runtime overhead')
    elif float(chosen_json['val_summary']['exp_delta']) > 0.0:
        lines.append('- result: positive expansion trend exists, but runtime overhead is still above the target threshold')
    else:
        lines.append('- result: no positive cross-family pilot trend yet under the current implementation')
    args.report_path.write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    main()
