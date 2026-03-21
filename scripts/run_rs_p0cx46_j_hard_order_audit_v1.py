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
from rs_cx8.common import load_nonholonomic_assets, load_nonholonomic_contexts, write_inputs_sha256


METHOD_SPECS = (
    ('CX34-A (Full)', 'rs_cx34.cx34_a_msr', 'outputs/rs_p0cx34_a_pilot_v1/chosen.json', None),
    ('CX46-J (No-Witness-Transfer)', 'rs_cx46.cx46_j_rrc', 'outputs/rs_p0cx46_j_rrc_public_v1/chosen.json', {'disable_witness_transfer': True}),
    ('CX46-J (No-Credit-Gate)', 'rs_cx46.cx46_j_rrc', 'outputs/rs_p0cx46_j_rrc_public_v1/chosen.json', {'disable_credit_gate': True}),
    ('CX46-J (Full)', 'rs_cx46.cx46_j_rrc', 'outputs/rs_p0cx46_j_rrc_public_v1/chosen.json', None),
)

ORDERS = (
    ('order_a', ('CX34-A (Full)', 'CX46-J (No-Witness-Transfer)', 'CX46-J (No-Credit-Gate)', 'CX46-J (Full)')),
    ('order_b', ('CX46-J (No-Witness-Transfer)', 'CX46-J (No-Credit-Gate)', 'CX46-J (Full)', 'CX34-A (Full)')),
    ('order_c', ('CX46-J (No-Credit-Gate)', 'CX46-J (Full)', 'CX34-A (Full)', 'CX46-J (No-Witness-Transfer)')),
    ('order_d', ('CX46-J (Full)', 'CX34-A (Full)', 'CX46-J (No-Witness-Transfer)', 'CX46-J (No-Credit-Gate)')),
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Run hard order audit for CX46-J runtime attribution.')
    p.add_argument('--split-root', type=Path, default=Path('data/split/calib_hard_v1'))
    p.add_argument('--hard-root', type=Path, default=Path('data/benchmark/rs_root_hard_v2_order_audit_subset_v1/test'))
    p.add_argument('--ours-checkpoint', type=Path, default=Path('outputs/checkpoints/exp3_final_manual_v11b.pt'))
    p.add_argument('--device', type=str, default='cuda')
    p.add_argument('--fixed-cap', type=int, default=20000)
    p.add_argument('--max-cases', type=int, default=0)
    p.add_argument('--outputs-root', type=Path, default=Path('outputs/rs_p0cx46_j_hard_order_audit_v1'))
    p.add_argument('--reports-root', type=Path, default=Path('reports'))
    return p.parse_args()


def _read_split_rows(path: Path) -> list[dict[str, Any]]:
    with path.open('r', newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames: list[str] = []
    seen = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _summary(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row[k] for k in keys)].append(row)
    out = []
    for key, grp in sorted(grouped.items()):
        item = {k: key[i] for i, k in enumerate(keys)}
        item.update(
            {
                'num_cases': int(len(grp)),
                'success_rate': float(np.mean([float(r['success']) for r in grp])),
                'avg_expansions': float(np.mean([float(r['expansions']) for r in grp])),
                'avg_time_ms': float(np.mean([float(r['time_ms']) for r in grp])),
                'avg_prep_ms': float(np.mean([float(r['prep_ms']) for r in grp])),
                'avg_plan_ms': float(np.mean([float(r['plan_ms']) for r in grp])),
                'avg_witness_hits': float(np.mean([float(r.get('witness_hits', 0.0)) for r in grp])),
                'avg_credit_gate_skips': float(np.mean([float(r.get('credit_gate_skips', 0.0)) for r in grp])),
            }
        )
        out.append(item)
    return out


def _delta(summary_rows: list[dict[str, Any]], group_keys: tuple[str, ...], baseline_method: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], dict[str, dict[str, Any]]] = defaultdict(dict)
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
                    'prep_delta_ms': float(row['avg_prep_ms']) - float(base['avg_prep_ms']),
                    'plan_delta_ms': float(row['avg_plan_ms']) - float(base['avg_plan_ms']),
                    'witness_hit_delta': float(row['avg_witness_hits']) - float(base.get('avg_witness_hits', 0.0)),
                    'credit_skip_delta': float(row['avg_credit_gate_skips']) - float(base.get('avg_credit_gate_skips', 0.0)),
                }
            )
            out.append(item)
    return out


def _load_method_specs():
    specs = {}
    for label, mod_name, chosen_json, ablation in METHOD_SPECS:
        specs[label] = {
            'label': label,
            'module': importlib.import_module(mod_name),
            'chosen_json': Path(chosen_json),
            'ablation': ablation,
        }
    return specs


def _load_params(spec) -> Any:
    data = json.loads(spec['chosen_json'].read_text(encoding='utf-8'))
    if 'params' in data:
        params_data = data['params']
    else:
        params_data = data['dev_choice']['params']
    module = spec['module']
    param_type = module.param_grid()[0].__class__
    return param_type(**params_data)


def _fit_memory(spec, train_assets, val_contexts, predictor, cfg, device: str, out_dir: Path):
    params_obj = _load_params(spec)
    memory = spec['module'].fit_variant(train_assets, val_contexts, predictor, cfg, params_obj, out_dir, device, None)
    return params_obj, memory


def _eval_once(asset: dict[str, Any], label: str, spec: dict[str, Any], params_obj, memory, predictor, cfg, cap: int, device: str, position: int, order_name: str) -> dict[str, Any]:
    module = spec['module']
    asset['case']['_cx44_sample_name'] = str(asset['path'].name)
    field = module.build_nonholonomic_field(asset['case'], predictor, cfg, params_obj, memory)
    bundle = asset['case'].get('_cx21_bundle', asset['bundle'])
    prep_t0 = time.perf_counter()
    policy = module.make_policy(memory, params_obj, asset['case'], bundle, field, device, ablation=spec['ablation'])
    prep_ms = (time.perf_counter() - prep_t0) * 1000.0
    plan_t0 = time.perf_counter()
    plan = run_hybrid_with_policy(asset['case'], field, int(cap), successor_policy=policy, record_expanded=False)
    wall_plan_ms = (time.perf_counter() - plan_t0) * 1000.0
    stats = getattr(policy, 'stats', {}) if hasattr(policy, 'stats') else {}
    return {
        'sample_name': str(asset['path'].name),
        'scenario': str(asset['case']['scenario']),
        'order_name': str(order_name),
        'position': int(position),
        'method': str(label),
        'success': float(plan.success),
        'expansions': float(plan.expansions),
        'time_ms': float(plan.runtime_ms + prep_ms),
        'prep_ms': float(prep_ms),
        'plan_ms': float(plan.runtime_ms),
        'wall_plan_ms': float(wall_plan_ms),
        'witness_hits': float(stats.get('witness_hits', 0.0)),
        'credit_gate_skips': float(stats.get('credit_gate_skips', 0.0)),
    }


def main() -> None:
    args = parse_args()
    args.outputs_root.mkdir(parents=True, exist_ok=True)
    args.reports_root.mkdir(parents=True, exist_ok=True)

    specs = _load_method_specs()
    predictor = NeuralHeuristicPredictor(args.ours_checkpoint, device=args.device, gaussian_sigma=2.5)
    cfg = CXGlobalConfig()
    train_rows = _read_split_rows(args.split_root / 'calib_train.csv')
    val_rows = _read_split_rows(args.split_root / 'calib_val.csv')
    train_files = [Path(r['path']) for r in train_rows]
    val_files = [Path(r['path']) for r in val_rows]
    hard_files = sorted(args.hard_root.glob('sample_*.npz'))
    if int(args.max_cases) > 0:
        hard_files = hard_files[: int(args.max_cases)]
    train_assets = load_nonholonomic_assets(train_files, predictor, cfg, int(args.fixed_cap), tag='cx46j-order:train')
    val_contexts = load_nonholonomic_contexts(val_files, predictor, cfg, tag='cx46j-order:val')
    hard_contexts = load_nonholonomic_contexts(hard_files, predictor, cfg, tag='cx46j-order:hard')

    fitted = {}
    for label, spec in specs.items():
        print(f'[cx46j-order] fitting {label}', flush=True)
        params_obj, memory = _fit_memory(spec, train_assets, val_contexts, predictor, cfg, args.device, args.outputs_root / f'fit_{label.replace(" ", "_").replace("(", "").replace(")", "")}')
        fitted[label] = (spec, params_obj, memory)

    rows: list[dict[str, Any]] = []
    total = len(hard_contexts)
    for idx, asset in enumerate(hard_contexts, start=1):
        for order_name, order in ORDERS:
            for position, label in enumerate(order):
                spec, params_obj, memory = fitted[label]
                rows.append(_eval_once(asset, label, spec, params_obj, memory, predictor, cfg, int(args.fixed_cap), args.device, position, order_name))
        if idx % 5 == 0 or idx == total:
            print(f'[cx46j-order] {idx}/{total}', flush=True)

    _write_csv(args.outputs_root / 'order_case_rows.csv', rows)
    summary = _summary(rows, ('order_name', 'position', 'method'))
    overall = _summary(rows, ('method',))
    delta_vs_cx34 = _delta(overall, tuple(), 'CX34-A (Full)')
    delta_vs_nowt = _delta(overall, tuple(), 'CX46-J (No-Witness-Transfer)')
    delta_vs_nocg = _delta(overall, tuple(), 'CX46-J (No-Credit-Gate)')
    _write_csv(args.outputs_root / 'order_summary.csv', summary)
    _write_csv(args.outputs_root / 'overall_summary.csv', overall)
    _write_csv(args.outputs_root / 'delta_overall_vs_cx34.csv', delta_vs_cx34)
    _write_csv(args.outputs_root / 'delta_overall_vs_nowt.csv', delta_vs_nowt)
    _write_csv(args.outputs_root / 'delta_overall_vs_nocg.csv', delta_vs_nocg)
    write_inputs_sha256([args.ours-checkpoint if False else args.ours_checkpoint, args.split_root / 'calib_train.csv', args.split_root / 'calib_val.csv'] + train_files + val_files + hard_files, args.outputs_root / 'inputs_sha256.json')

    lines = [
        '# CX46-J Hard Order Audit V1',
        '',
        '- protocol: Latin-square hard order audit over `CX34-A (Full)`, `CX46-J (No-Witness-Transfer)`, `CX46-J (No-Credit-Gate)`, and `CX46-J (Full)`',
        f'- hard root: `{args.hard_root}`',
        f'- num_cases: `{len(hard_contexts)}`',
        f'- inputs sha256: `{args.outputs_root / "inputs_sha256.json"}`',
        '',
        '## Overall vs `CX34-A (Full)`',
    ]
    for row in delta_vs_cx34:
        lines.append(f"- `{row['method']}`: success_delta_pp=`{float(row['success_delta_pp']):.3f}`, exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`, prep_delta_ms=`{float(row['prep_delta_ms']):.3f}`, plan_delta_ms=`{float(row['plan_delta_ms']):.3f}`, witness_hit_delta=`{float(row['witness_hit_delta']):.3f}`, credit_skip_delta=`{float(row['credit_skip_delta']):.3f}`")
    lines += ['', '## Overall vs `CX46-J (No-Witness-Transfer)`']
    for row in delta_vs_nowt:
        lines.append(f"- `{row['method']}`: success_delta_pp=`{float(row['success_delta_pp']):.3f}`, exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`, prep_delta_ms=`{float(row['prep_delta_ms']):.3f}`, plan_delta_ms=`{float(row['plan_delta_ms']):.3f}`, witness_hit_delta=`{float(row['witness_hit_delta']):.3f}`, credit_skip_delta=`{float(row['credit_skip_delta']):.3f}`")
    lines += ['', '## Overall vs `CX46-J (No-Credit-Gate)`']
    for row in delta_vs_nocg:
        lines.append(f"- `{row['method']}`: success_delta_pp=`{float(row['success_delta_pp']):.3f}`, exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`, prep_delta_ms=`{float(row['prep_delta_ms']):.3f}`, plan_delta_ms=`{float(row['plan_delta_ms']):.3f}`, witness_hit_delta=`{float(row['witness_hit_delta']):.3f}`, credit_skip_delta=`{float(row['credit_skip_delta']):.3f}`")
    lines += ['', '## Absolute Order Readout']
    for row in summary:
        lines.append(f"- `{row['order_name']}` / pos=`{row['position']}` / `{row['method']}`: success_rate=`{float(row['success_rate']):.3f}`, avg_expansions=`{float(row['avg_expansions']):.3f}`, avg_time_ms=`{float(row['avg_time_ms']):.3f}`, avg_witness_hits=`{float(row['avg_witness_hits']):.3f}`, avg_credit_gate_skips=`{float(row['avg_credit_gate_skips']):.3f}`")
    (args.reports_root / 'rs_p0cx46_j_hard_order_audit_v1.md').write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    main()
