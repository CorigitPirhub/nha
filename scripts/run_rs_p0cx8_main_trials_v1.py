from __future__ import annotations

import argparse
import csv
import importlib
import json
import math
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baselines.common import load_grid_sample
from network.inference import NeuralHeuristicPredictor
from rs_cx.common import CXGlobalConfig, run_standard_astar
from rs_cx8.common import (
    accepted_cx3d_standard,
    choose_calib_split,
    load_nonholonomic_assets,
    load_nonholonomic_contexts,
    run_hybrid_with_policy,
    sha256_file,
    write_inputs_sha256,
)
from scripts.evaluate_baselines import _path_length

CX8_MODULES = {
    'CX8-A': 'rs_cx8.cx8_a_app',
    'CX8-B': 'rs_cx8.cx8_b_kfm',
    'CX8-D': 'rs_cx8.cx8_d_bca',
    'CX8-C': 'rs_cx8.cx8_c_tdg',
}

ORDER = ['CX8-A', 'CX8-B', 'CX8-D', 'CX8-C']


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Run strict P0-CX8 main trials.')
    p.add_argument('--benchmark-root', type=Path, default=Path('data/benchmark'))
    p.add_argument('--hard-benchmark-root', type=Path, default=Path('data/benchmark/rs_root_hard_v2'))
    p.add_argument('--parasol-root', type=Path, default=Path('data/benchmark/parasol_narrow/test'))
    p.add_argument('--ours-checkpoint', type=Path, default=Path('outputs/checkpoints/exp3_final_manual_v11b.pt'))
    p.add_argument('--device', type=str, default='cuda')
    p.add_argument('--seed', type=int, default=7)
    p.add_argument('--fixed-cap-exp3', type=int, default=7000)
    p.add_argument('--fixed-cap-exp4', type=int, default=20000)
    p.add_argument('--variants', type=str, default='CX8-A,CX8-B,CX8-D,CX8-C')
    p.add_argument('--skip-standard', action='store_true')
    p.add_argument('--max-calib-train-cases', type=int, default=0)
    p.add_argument('--max-calib-val-cases', type=int, default=0)
    p.add_argument('--max-public-cases', type=int, default=0)
    p.add_argument('--max-hard-test-cases', type=int, default=0)
    p.add_argument('--budgets', type=str, default='exp3,exp4')
    p.add_argument('--split-root', type=Path, default=Path())
    p.add_argument('--calib-train-names', type=str, default='')
    p.add_argument('--calib-val-names', type=str, default='')
    p.add_argument('--public-names', type=str, default='')
    p.add_argument('--hard-test-names', type=str, default='')
    p.add_argument('--out-root', type=Path, default=Path('outputs/rs_p0cx8_main_trials_v1'))
    p.add_argument('--reports-root', type=Path, default=Path('reports'))
    return p.parse_args()


def _variants(raw: str) -> list[str]:
    vals = [x.strip() for x in str(raw).split(',') if x.strip()]
    return [k for k in ORDER if k in vals]


def _maybe_named_files(root: Path, raw: str) -> list[Path] | None:
    names = [x.strip() for x in str(raw).split(',') if x.strip()]
    if not names:
        return None
    return [root / name for name in names]


def _split_csv_files(path: Path) -> list[Path]:
    if not path or not path.exists():
        return []
    with path.open('r', newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    return [Path(row['path']) for row in rows]


def _summary(rows: list[dict[str, Any]], *, baseline: str) -> dict[str, Any]:
    by = defaultdict(list)
    for row in rows:
        by[(str(row['benchmark']), str(row['budget']), str(row['method']))].append(row)
    summaries = []
    for (benchmark, budget, method), grp in sorted(by.items()):
        succ = np.asarray([float(r['success']) for r in grp], dtype=np.float64)
        exp = np.asarray([float(r['expansions']) for r in grp], dtype=np.float64)
        tim = np.asarray([float(r['time_ms']) for r in grp], dtype=np.float64)
        path = np.asarray([float(r['path_length']) for r in grp if np.isfinite(float(r['path_length']))], dtype=np.float64)
        summaries.append({
            'benchmark': benchmark,
            'budget': budget,
            'method': method,
            'num_cases': int(len(grp)),
            'success_rate': float(np.mean(succ)),
            'avg_expansions': float(np.mean(exp)),
            'avg_time_ms': float(np.mean(tim)),
            'avg_path_length': float(np.mean(path)) if path.size else float('nan'),
        })
    idx = {(r['benchmark'], r['budget'], r['method']): r for r in summaries}
    deltas = []
    methods = sorted({r['method'] for r in summaries if r['method'] != baseline})
    keys = sorted({(r['benchmark'], r['budget']) for r in summaries})
    for benchmark, budget in keys:
        base = idx.get((benchmark, budget, baseline))
        if base is None:
            continue
        for method in methods:
            cur = idx.get((benchmark, budget, method))
            if cur is None:
                continue
            deltas.append({
                'benchmark': benchmark,
                'budget': budget,
                'method': method,
                'baseline': baseline,
                'success_delta_pp': 100.0 * (float(cur['success_rate']) - float(base['success_rate'])),
                'exp_delta': float(base['avg_expansions']) - float(cur['avg_expansions']),
                'time_delta_ms': float(base['avg_time_ms']) - float(cur['avg_time_ms']),
                'path_delta': (float(base['avg_path_length']) - float(cur['avg_path_length'])) if np.isfinite(float(base['avg_path_length'])) and np.isfinite(float(cur['avg_path_length'])) else float('nan'),
            })
    return {'summary_rows': summaries, 'delta_rows': deltas}


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _path_len_from_result(result) -> float:
    return float(_path_length([(float(p[0]), float(p[1])) for p in result.path])) if result.path.size > 0 else float('nan')


def _eval_case(asset: dict[str, Any], method: str, cap: int, *, module=None, memory=None, params_obj=None, predictor=None, cfg=None, device='cuda') -> dict[str, Any]:
    cache = asset.setdefault('eval_cache', {})
    key = (str(method), int(cap))
    if key in cache:
        return cache[key]
    case = asset['case']
    if method == 'Hybrid A* (RS)':
        field = asset['bundle']['rs_base']
        policy = None
    elif method == 'CX3-D':
        field = asset['field']
        policy = None
    else:
        field = module.build_nonholonomic_field(case, predictor, cfg, params_obj, memory)
        policy = module.make_policy(memory, params_obj, case, asset['bundle'], field, device)
    res = run_hybrid_with_policy(case, field, int(cap), successor_policy=policy, record_expanded=False)
    row = {
        'success': float(res.success),
        'expansions': float(res.expansions),
        'time_ms': float(res.runtime_ms),
        'path_length': _path_len_from_result(res),
    }
    cache[key] = row
    return row


def _select_trial(trials: list[dict[str, Any]]) -> dict[str, Any]:
    ranked = []
    for tr in trials:
        s = tr['val_delta']
        path_delta = float(s['path_delta']) if np.isfinite(float(s['path_delta'])) else 0.0
        if path_delta < -0.75:
            continue
        ranked.append((float(s['success_delta_pp']), float(s['exp_delta']), float(s['time_delta_ms']), tr))
    if not ranked:
        ranked = [(float(t['val_delta']['success_delta_pp']), float(t['val_delta']['exp_delta']), float(t['val_delta']['time_delta_ms']), t) for t in trials]
    ranked.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
    return ranked[0][3]


def _standard_eval(benchmark_root: Path, predictor: NeuralHeuristicPredictor, *, max_mp: int = 800, max_csm: int = 400) -> dict[str, dict[str, Any]]:
    out = {}
    for name, limit in [('mp', max_mp), ('csm', max_csm)]:
        rows = []
        files = sorted((benchmark_root / name / 'test').glob('sample_*.npz'))[:int(limit)]
        for i, path in enumerate(files, start=1):
            sample = load_grid_sample(path)
            _, field = accepted_cx3d_standard(sample, predictor)
            res = run_standard_astar(sample, field, 50000)
            rows.append({'success': float(res['success']), 'expansions': float(res['expansions']), 'time_ms': float(res['runtime_ms'])})
            if i % 100 == 0 or i == len(files):
                print(f'[rs-p0cx8:standard] {name} {i}/{len(files)}')
        out[name] = {
            'num_cases': int(len(rows)),
            'success_rate': float(np.mean([r['success'] for r in rows])) if rows else float('nan'),
            'avg_expansions': float(np.mean([r['expansions'] for r in rows])) if rows else float('nan'),
            'avg_time_ms': float(np.mean([r['time_ms'] for r in rows])) if rows else float('nan'),
        }
    return out


def main() -> None:
    args = parse_args()
    predictor = NeuralHeuristicPredictor(args.ours_checkpoint, device=args.device, gaussian_sigma=2.5)
    cfg = CXGlobalConfig()
    args.out_root.mkdir(parents=True, exist_ok=True)
    args.reports_root.mkdir(parents=True, exist_ok=True)

    dev_files = sorted((args.hard_benchmark_root / 'dev').glob('sample_*.npz'))
    split = choose_calib_split(dev_files, int(args.seed))
    split_train_files = _split_csv_files(args.split_root / 'calib_train.csv') if str(args.split_root) not in {'', '.'} else []
    split_val_files = _split_csv_files(args.split_root / 'calib_val.csv') if str(args.split_root) not in {'', '.'} else []
    calib_train_files = split_train_files or _maybe_named_files(args.hard_benchmark_root / 'dev', args.calib_train_names) or split['calib_train']
    calib_val_files = split_val_files or _maybe_named_files(args.hard_benchmark_root / 'dev', args.calib_val_names) or split['calib_val']
    if int(args.max_calib_train_cases) > 0:
        calib_train_files = calib_train_files[: int(args.max_calib_train_cases)]
    if int(args.max_calib_val_cases) > 0:
        calib_val_files = calib_val_files[: int(args.max_calib_val_cases)]
    print(f'[rs-p0cx8] calib_train={len(calib_train_files)} calib_val={len(calib_val_files)}')

    t0 = time.perf_counter()
    calib_train_assets = load_nonholonomic_assets(calib_train_files, predictor, cfg, int(args.fixed_cap_exp3), tag='rs-p0cx8:calib-train')
    calib_val_assets = load_nonholonomic_assets(calib_val_files, predictor, cfg, int(args.fixed_cap_exp3), tag='rs-p0cx8:calib-val')

    selected: dict[str, Any] = {}
    for key in _variants(args.variants):
        mod = importlib.import_module(CX8_MODULES[key])
        deps = None
        if key == 'CX8-C':
            deps = {
                'APP': {'memory': selected['CX8-A']['memory'], 'params': selected['CX8-A']['params_obj']},
                'KFM': {'memory': selected['CX8-B']['memory'], 'params': selected['CX8-B']['params_obj']},
                'BCA': {'memory': selected['CX8-D']['memory'], 'params': selected['CX8-D']['params_obj']},
            }
        trials = []
        trial_root = args.out_root / key.lower().replace('-', '_') / 'trials'
        for idx, params_obj in enumerate(mod.param_grid(), start=1):
            fit_dir = trial_root / f'trial_{idx:02d}'
            memory = mod.fit_variant(calib_train_assets, calib_val_assets, predictor, cfg, params_obj, fit_dir, args.device, dependencies=deps)
            rows = []
            for asset in calib_val_assets:
                base = _eval_case(asset, 'CX3-D', int(args.fixed_cap_exp3))
                cur = _eval_case(asset, key, int(args.fixed_cap_exp3), module=mod, memory=memory, params_obj=params_obj, predictor=predictor, cfg=cfg, device=args.device)
                rows.append({
                    'success_delta': float(cur['success']) - float(base['success']),
                    'exp_delta': float(base['expansions']) - float(cur['expansions']),
                    'time_delta': float(base['time_ms']) - float(cur['time_ms']),
                    'path_delta': float(base['path_length']) - float(cur['path_length']) if np.isfinite(float(base['path_length'])) and np.isfinite(float(cur['path_length'])) else float('nan'),
                })
            val_delta = {
                'success_delta_pp': 100.0 * float(np.mean([r['success_delta'] for r in rows])) if rows else 0.0,
                'exp_delta': float(np.mean([r['exp_delta'] for r in rows])) if rows else 0.0,
                'time_delta_ms': float(np.mean([r['time_delta'] for r in rows])) if rows else 0.0,
                'path_delta': float(np.nanmean([r['path_delta'] for r in rows])) if rows else float('nan'),
            }
            trials.append({'params_obj': params_obj, 'memory': memory, 'val_delta': val_delta, 'fit_dir': fit_dir})
            print(f'[rs-p0cx8:{key}] trial={idx} params={params_obj} val_delta={val_delta}')
        chosen = _select_trial(trials)
        chosen_dir = args.out_root / key.lower().replace('-', '_')
        chosen_dir.mkdir(parents=True, exist_ok=True)
        chosen_json = {
            'params': chosen['params_obj'].__dict__,
            'val_delta': chosen['val_delta'],
            'fit_dir': str(chosen['fit_dir']),
            'best_val_loss': float(chosen['memory'].get('best_val_loss', float('nan'))),
            'train_samples': int(chosen['memory'].get('train_samples', 0)),
            'val_samples': int(chosen['memory'].get('val_samples', 0)),
        }
        (chosen_dir / 'chosen.json').write_text(json.dumps(chosen_json, indent=2, ensure_ascii=False), encoding='utf-8')
        selected[key] = {
            'module': mod,
            'memory': chosen['memory'],
            'params_obj': chosen['params_obj'],
            'chosen': chosen_json,
        }
        print(f'[rs-p0cx8:{key}] chosen={chosen_json}')

    public_test_files = _maybe_named_files(args.parasol_root, args.public_names) or sorted(args.parasol_root.glob('sample_*.npz'))
    hard_test_files = _maybe_named_files(args.hard_benchmark_root / 'test', args.hard_test_names) or sorted((args.hard_benchmark_root / 'test').glob('sample_*.npz'))
    if int(args.max_public_cases) > 0:
        public_test_files = public_test_files[: int(args.max_public_cases)]
    if int(args.max_hard_test_cases) > 0:
        hard_test_files = hard_test_files[: int(args.max_hard_test_cases)]
    public_assets = load_nonholonomic_contexts(public_test_files, predictor, cfg, tag='rs-p0cx8:public-test')
    hard_test_assets = load_nonholonomic_contexts(hard_test_files, predictor, cfg, tag='rs-p0cx8:hard-test')

    case_rows: list[dict[str, Any]] = []
    budget_keys = [x.strip() for x in str(args.budgets).split(',') if x.strip()]
    budgets = []
    for key in budget_keys:
        if key == 'exp3':
            budgets.append(('exp3', int(args.fixed_cap_exp3)))
        elif key == 'exp4':
            budgets.append(('exp4', int(args.fixed_cap_exp4)))
        else:
            raise ValueError(f'unknown budget key: {key}')
    for benchmark_name, assets in [('public_parasol', public_assets), ('rs_root_hard_v2_test', hard_test_assets)]:
        total = len(assets)
        for i, asset in enumerate(assets, start=1):
            sample_name = asset['path'].name
            scenario = str(asset['case']['scenario'])
            source = str(asset['path'])
            for budget_name, cap in budgets:
                for method in ['Hybrid A* (RS)', 'CX3-D'] + _variants(args.variants):
                    if method in {'Hybrid A* (RS)', 'CX3-D'}:
                        row = _eval_case(asset, method, cap)
                    else:
                        ent = selected[method]
                        row = _eval_case(asset, method, cap, module=ent['module'], memory=ent['memory'], params_obj=ent['params_obj'], predictor=predictor, cfg=cfg, device=args.device)
                    case_rows.append({
                        'benchmark': benchmark_name,
                        'budget': budget_name,
                        'sample_name': sample_name,
                        'scenario': scenario,
                        'source_path': source,
                        'method': method,
                        **row,
                    })
            if i % 5 == 0 or i == total:
                print(f'[rs-p0cx8:{benchmark_name}] {i}/{total}')

    summary_pack = _summary(case_rows, baseline='CX3-D')
    summary_rows = summary_pack['summary_rows']
    delta_rows = summary_pack['delta_rows']
    _write_csv(args.out_root / 'case_rows.csv', case_rows)
    _write_csv(args.out_root / 'summary_rows.csv', summary_rows)
    _write_csv(args.out_root / 'delta_rows.csv', delta_rows)

    standard_summary = {} if args.skip_standard else _standard_eval(args.benchmark_root, predictor)
    (args.out_root / 'standard_summary.json').write_text(json.dumps(standard_summary, indent=2, ensure_ascii=False), encoding='utf-8')

    inputs = [
        args.ours_checkpoint,
        args.hard_benchmark_root / 'meta.json',
    ] + calib_train_files + calib_val_files + public_test_files + hard_test_files
    write_inputs_sha256(inputs, args.out_root / 'inputs_sha256.json')

    best_public = [r for r in delta_rows if r['benchmark'] == 'public_parasol' and r['budget'] == 'exp4' and r['method'] in _variants(args.variants)]
    best_public.sort(key=lambda r: (float(r['success_delta_pp']), float(r['exp_delta']), float(r['time_delta_ms'])), reverse=True)
    winner = best_public[0] if best_public else None

    lines = [
        '# P0-CX8 Main Trials',
        '',
        '- strict selection split: `rs_root_hard_v2/dev -> calib_train/calib_val`',
        f"- calib_train cases: `{len(calib_train_files)}`",
        f"- calib_val cases: `{len(calib_val_files)}`",
        f"- public test cases: `{len(public_test_files)}`",
        f"- hard_v2 test cases: `{len(hard_test_files)}`",
        f"- budgets evaluated: `{[name for name, _ in budgets]}`",
        f"- inputs sha256: `{args.out_root / 'inputs_sha256.json'}`",
        '',
        '## Chosen Variants',
    ]
    for key in _variants(args.variants):
        ch = selected[key]['chosen']
        lines.append(f"- `{key}` params=`{ch['params']}` val_delta=`{ch['val_delta']}` train/val samples=`{ch['train_samples']}`/`{ch['val_samples']}`")
    lines += ['', '## Final Test Summary vs Accepted `CX3-D`']
    for row in delta_rows:
        if row['method'] not in _variants(args.variants):
            continue
        lines.append(
            f"- `{row['benchmark']} / {row['budget']} / {row['method']}`: success_delta_pp=`{row['success_delta_pp']:.3f}`, exp_delta=`{row['exp_delta']:.3f}`, time_delta_ms=`{row['time_delta_ms']:.3f}`, path_delta=`{row['path_delta']:.3f}`"
        )
    if standard_summary:
        lines += ['', '## Ordinary Support (`mp/csm`)']
        for name, stats in standard_summary.items():
            lines.append(f"- `{name}` accepted-CX3D-compatible support: success=`{stats['success_rate']:.6f}`, expansions=`{stats['avg_expansions']:.3f}`, time_ms=`{stats['avg_time_ms']:.3f}`")
    lines += ['', '## Verdict']
    if winner is not None and (float(winner['success_delta_pp']) > 0.0 or float(winner['exp_delta']) > 15.0):
        lines.append(f"- strongest public candidate: `{winner['method']}` on `{winner['budget']}` with success_delta_pp=`{winner['success_delta_pp']:.3f}`, exp_delta=`{winner['exp_delta']:.3f}`")
    else:
        lines.append('- no `CX8` candidate establishes a decisive public strict advantage over accepted `CX3-D` in this round')
    (args.reports_root / 'rs_p0cx8_main_trials_v1.md').write_text('\n'.join(lines), encoding='utf-8')

    manifest = {
        'version': 'rs_p0cx8_main_trials_v1',
        'runtime_hours': float((time.perf_counter() - t0) / 3600.0),
        'checkpoint_sha256': sha256_file(args.ours_checkpoint),
        'chosen_variants': {k: selected[k]['chosen'] for k in _variants(args.variants)},
        'split': {
            'calib_train': [p.name for p in calib_train_files],
            'calib_val': [p.name for p in calib_val_files],
        },
    }
    (args.out_root / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    main()
