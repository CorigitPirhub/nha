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
from rs_cx21.common import run_hybrid_with_policy
from rs_cx24.common import build_frozen_haa_teacher
from rs_cx8.common import load_nonholonomic_assets, load_nonholonomic_contexts, write_inputs_sha256


BASELINES: list[tuple[str, str, str]] = [
    ('CX33-B', 'rs_cx33.cx33_b_bsr', 'outputs/rs_p0cx33_b_pilot_v1/chosen.json'),
    ('CX34-A', 'rs_cx34.cx34_a_msr', 'outputs/rs_p0cx34_a_pilot_v1/chosen.json'),
    ('CX36-B', 'rs_cx36.cx36_b_etc', 'outputs/rs_p0cx36_rerun_v2/rs_p0cx36_b_pilot_v1/chosen.json'),
    ('CX39-C', 'rs_cx39.cx39_c_cbc', 'outputs/rs_p0cx39_c_pilot_v1/chosen.json'),
    ('CX40-A', 'rs_cx40.cx40_a_cas', 'outputs/rs_p0cx40_a_pilot_v1/chosen.json'),
    ('CX41-B', 'rs_cx41.cx41_b_fdr', 'outputs/rs_p0cx41_b_pilot_v1/chosen.json'),
    ('CX42-B', 'rs_cx42.cx42_b_qcr', 'outputs/rs_p0cx42_b_pilot_v1/chosen.json'),
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Unified public comparison for RS+CX34-A+CX42-B candidate line.')
    p.add_argument('--split-root', type=Path, default=Path('data/split/calib_hard_v1'))
    p.add_argument('--parasol-root', type=Path, default=Path('data/benchmark/parasol_narrow/test'))
    p.add_argument('--ours-checkpoint', type=Path, default=Path('outputs/checkpoints/exp3_final_manual_v11b.pt'))
    p.add_argument('--device', type=str, default='cuda')
    p.add_argument('--dev-cap', type=int, default=20000)
    p.add_argument('--exp4-cap', type=int, default=20000)
    p.add_argument('--reports-root', type=Path, default=Path('reports'))
    p.add_argument('--outputs-root', type=Path, default=Path('outputs/rs_p0cx42_public_compare_v1'))
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
        item.update(
            {
                'num_cases': len(grp),
                'success_rate': float(np.mean([float(r['success']) for r in grp])),
                'avg_expansions': float(np.mean([float(r['expansions']) for r in grp])),
                'avg_time_ms': float(np.mean([float(r['time_ms']) for r in grp])),
            }
        )
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
            item.update(
                {
                    'method': method,
                    'baseline': baseline_method,
                    'success_delta_pp': 100.0 * (float(row['success_rate']) - float(base['success_rate'])),
                    'exp_delta': float(base['avg_expansions']) - float(row['avg_expansions']),
                    'mean_time_overhead_ratio': (float(row['avg_time_ms']) - float(base['avg_time_ms'])) / max(float(base['avg_time_ms']), 1e-6),
                }
            )
            out.append(item)
    return out


def _family_delta(rows: list[dict[str, Any]], baseline_method: str) -> list[dict[str, Any]]:
    return _delta(_summary(rows, ('scenario', 'method')), ('scenario',), baseline_method)


def _eval_cx3(public_contexts, cap: int) -> list[dict[str, Any]]:
    rows = []
    total = len(public_contexts)
    for idx, asset in enumerate(public_contexts, start=1):
        plan = run_hybrid_with_policy(asset['case'], asset['field'], int(cap), successor_policy=None, record_expanded=False)
        rows.append(
            {
                'dataset': 'exp4',
                'sample_name': str(asset['path'].name),
                'scenario': str(asset['case']['scenario']),
                'method': 'CX3-D',
                'success': float(plan.success),
                'expansions': float(plan.expansions),
                'time_ms': float(plan.runtime_ms),
            }
        )
        if idx % 5 == 0 or idx == total:
            print(f'[cx42cmp:CX3-D] {idx}/{total}', flush=True)
    return rows


def _load_params(mod, chosen_json: Path):
    data = json.loads(chosen_json.read_text(encoding='utf-8'))
    param_type = mod.param_grid()[0].__class__
    return param_type(**data['params'])


def _eval_module(label: str, mod_name: str, chosen_json: Path, predictor, cfg, train_assets, val_contexts, public_contexts, teacher, device: str, cap: int) -> tuple[list[dict[str, Any]], dict[str, Any], Any, Any]:
    mod = importlib.import_module(mod_name)
    params = _load_params(mod, chosen_json)
    memory = mod.fit_variant(train_assets, val_contexts, predictor, cfg, params, chosen_json.parent / '_compare_fit', device, {'haa_teacher': teacher})
    rows = []
    total = len(public_contexts)
    for idx, asset in enumerate(public_contexts, start=1):
        field = mod.build_nonholonomic_field(asset['case'], predictor, cfg, params, memory)
        bundle = asset['case'].get('_cx21_bundle', asset['bundle'])
        prep_t0 = time.perf_counter()
        policy = mod.make_policy(memory, params, asset['case'], bundle, field, device, ablation=None)
        prep_ms = (time.perf_counter() - prep_t0) * 1000.0
        plan = run_hybrid_with_policy(asset['case'], field, int(cap), successor_policy=policy, record_expanded=False)
        rows.append(
            {
                'dataset': 'exp4',
                'sample_name': str(asset['path'].name),
                'scenario': str(asset['case']['scenario']),
                'method': f'{label} (Full)',
                'success': float(plan.success),
                'expansions': float(plan.expansions),
                'time_ms': float(plan.runtime_ms + prep_ms),
            }
        )
        if idx % 5 == 0 or idx == total:
            print(f'[{label} (Full)] {idx}/{total}', flush=True)
    return rows, memory, params, mod


def _eval_cx42_b_ablation(mod, memory, params, predictor, cfg, public_contexts, device: str, cap: int, label: str, ablation: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    total = len(public_contexts)
    for idx, asset in enumerate(public_contexts, start=1):
        field = mod.build_nonholonomic_field(asset['case'], predictor, cfg, params, memory)
        bundle = asset['case'].get('_cx21_bundle', asset['bundle'])
        prep_t0 = time.perf_counter()
        policy = mod.make_policy(memory, params, asset['case'], bundle, field, device, ablation=ablation)
        prep_ms = (time.perf_counter() - prep_t0) * 1000.0
        plan = run_hybrid_with_policy(asset['case'], field, int(cap), successor_policy=policy, record_expanded=False)
        rows.append(
            {
                'dataset': 'exp4',
                'sample_name': str(asset['path'].name),
                'scenario': str(asset['case']['scenario']),
                'method': label,
                'success': float(plan.success),
                'expansions': float(plan.expansions),
                'time_ms': float(plan.runtime_ms + prep_ms),
            }
        )
        if idx % 5 == 0 or idx == total:
            print(f'[{label}] {idx}/{total}', flush=True)
    return rows


def main():
    args = parse_args()
    args.outputs_root.mkdir(parents=True, exist_ok=True)
    args.reports_root.mkdir(parents=True, exist_ok=True)
    predictor = NeuralHeuristicPredictor(args.ours_checkpoint, device=args.device, gaussian_sigma=2.5)
    cfg = CXGlobalConfig()

    train_rows = _read_split_rows(args.split_root / 'calib_train.csv')
    val_rows = _read_split_rows(args.split_root / 'calib_val.csv')
    train_files = [Path(r['path']) for r in train_rows]
    val_files = [Path(r['path']) for r in val_rows]
    public_files = sorted(args.parasol_root.glob('sample_*.npz'))

    train_assets = load_nonholonomic_assets(train_files, predictor, cfg, int(args.dev_cap), tag='cx42cmp:calib-train')
    val_contexts = load_nonholonomic_contexts(val_files, predictor, cfg, tag='cx42cmp:calib-val')
    public_contexts = load_nonholonomic_contexts(public_files, predictor, cfg, tag='cx42cmp:public')
    teacher = build_frozen_haa_teacher(train_assets, val_contexts, predictor, cfg, args.device, args.outputs_root / 'haa_cache')

    rows = _eval_cx3(public_contexts, int(args.exp4_cap))
    fitted: dict[str, tuple[Any, Any, Any]] = {}
    for label, mod_name, chosen_json in BASELINES:
        module_rows, memory, params, mod = _eval_module(label, mod_name, Path(chosen_json), predictor, cfg, train_assets, val_contexts, public_contexts, teacher, args.device, int(args.exp4_cap))
        rows.extend(module_rows)
        fitted[label] = (mod, memory, params)

    cx42_mod, cx42_mem, cx42_params = fitted['CX42-B']
    rows.extend(_eval_cx42_b_ablation(cx42_mod, cx42_mem, cx42_params, predictor, cfg, public_contexts, args.device, int(args.exp4_cap), 'CX42-B (Always-CX34)', {'force_branch': 'cx34'}))
    rows.extend(_eval_cx42_b_ablation(cx42_mod, cx42_mem, cx42_params, predictor, cfg, public_contexts, args.device, int(args.exp4_cap), 'CX42-B (Always-CX41)', {'force_branch': 'cx41'}))

    _write_csv(args.outputs_root / 'public_case_rows.csv', rows)
    summary = _summary(rows, ('dataset', 'method'))
    delta_vs_cx3 = _delta(summary, ('dataset',), 'CX3-D')
    delta_vs_cx34 = _delta(summary, ('dataset',), 'CX34-A (Full)')
    delta_vs_cx42 = _delta(summary, ('dataset',), 'CX42-B (Full)')
    family_vs_cx3 = _family_delta(rows, 'CX3-D')
    family_vs_cx34 = _family_delta(rows, 'CX34-A (Full)')
    _write_csv(args.outputs_root / 'public_summary.csv', summary)
    _write_csv(args.outputs_root / 'public_delta_vs_cx3.csv', delta_vs_cx3)
    _write_csv(args.outputs_root / 'public_delta_vs_cx34.csv', delta_vs_cx34)
    _write_csv(args.outputs_root / 'public_delta_vs_cx42.csv', delta_vs_cx42)
    _write_csv(args.outputs_root / 'public_family_delta_vs_cx3.csv', family_vs_cx3)
    _write_csv(args.outputs_root / 'public_family_delta_vs_cx34.csv', family_vs_cx34)
    write_inputs_sha256([args.ours_checkpoint, args.split_root / 'calib_train.csv', args.split_root / 'calib_val.csv'] + train_files + val_files + public_files, args.outputs_root / 'inputs_sha256.json')

    lines = [
        '# RS + CX34-A + CX42-B Public Compare V1',
        '',
        '- protocol: unified public rerun under frozen `parasol_narrow exp4` semantics using the canonical chosen parameters for each branch',
        f"- output root: `{args.outputs_root}`",
        '',
        '## Public vs `CX3-D`',
    ]
    for row in delta_vs_cx3:
        lines.append(f"- `{row['method']}`: success_delta_pp=`{float(row['success_delta_pp']):.3f}`, exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`")
    lines += ['', '## Public vs `CX34-A (Full)`']
    for row in delta_vs_cx34:
        lines.append(f"- `{row['method']}`: success_delta_pp=`{float(row['success_delta_pp']):.3f}`, exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`")
    lines += ['', '## Public vs `CX42-B (Full)`']
    for row in delta_vs_cx42:
        lines.append(f"- `{row['method']}`: success_delta_pp=`{float(row['success_delta_pp']):.3f}`, exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`")
    lines += ['', '## Public Family Breakdown vs `CX34-A (Full)`']
    for row in family_vs_cx34:
        lines.append(f"- `{row['scenario']}` / `{row['method']}`: exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`")
    (args.reports_root / 'rs_p0cx42_public_compare_v1.md').write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    main()
