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
    p = argparse.ArgumentParser(description='Run P0-CX46 round11 public validation for review-credit scheduler.')
    p.add_argument('--split-root', type=Path, default=Path('data/split/calib_hard_v1'))
    p.add_argument('--parasol-root', type=Path, default=Path('data/benchmark/parasol_narrow/test'))
    p.add_argument('--benchmark-root', type=Path, default=Path('data/benchmark'))
    p.add_argument('--ours-checkpoint', type=Path, default=Path('outputs/checkpoints/exp3_final_manual_v11b.pt'))
    p.add_argument('--device', type=str, default='cuda')
    p.add_argument('--dev-cap', type=int, default=20000)
    p.add_argument('--exp4-cap', type=int, default=20000)
    p.add_argument('--max-mp-cases', type=int, default=800)
    p.add_argument('--max-csm-cases', type=int, default=400)
    p.add_argument('--dev-summary', type=Path, default=Path('outputs/rs_p0cx46_j_rrc_dev_v1/dev_summary.json'))
    p.add_argument('--outputs-root', type=Path, default=Path('outputs/rs_p0cx46_j_rrc_public_v1'))
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
        item.update({
            'num_cases': len(grp),
            'success_rate': float(np.mean([float(r['success']) for r in grp])),
            'avg_expansions': float(np.mean([float(r['expansions']) for r in grp])),
            'avg_time_ms': float(np.mean([float(r['time_ms']) for r in grp])),
        })
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
            item.update({
                'method': method,
                'baseline': baseline_method,
                'success_delta_pp': 100.0 * (float(row['success_rate']) - float(base['success_rate'])),
                'exp_delta': float(base['avg_expansions']) - float(row['avg_expansions']),
                'mean_time_overhead_ratio': (float(row['avg_time_ms']) - float(base['avg_time_ms'])) / max(float(base['avg_time_ms']), 1e-6),
            })
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
        stats = getattr(policy, 'stats', {}) if hasattr(policy, 'stats') else {}
        rows.append({
            'dataset': 'exp4',
            'sample_name': str(asset['path'].name),
            'scenario': str(asset['case']['scenario']),
            'method': method_name,
            'success': float(plan.success),
            'expansions': float(plan.expansions),
            'time_ms': float(plan.runtime_ms + prep_ms),
            'witness_hits': float(stats.get('witness_hits', 0.0)),
            'credit_gate_skips': float(stats.get('credit_gate_skips', 0.0)),
        })
        if idx % 5 == 0 or idx == total:
            print(f'[{method_name}] {idx}/{total}', flush=True)
    return rows


def _eval_cx3(public_contexts, cap: int):
    rows = []
    total = len(public_contexts)
    for idx, asset in enumerate(public_contexts, start=1):
        plan = run_hybrid_with_policy(asset['case'], asset['field'], int(cap), successor_policy=None, record_expanded=False)
        rows.append({
            'dataset': 'exp4',
            'sample_name': str(asset['path'].name),
            'scenario': str(asset['case']['scenario']),
            'method': 'CX3-D',
            'success': float(plan.success),
            'expansions': float(plan.expansions),
            'time_ms': float(plan.runtime_ms),
        })
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
                print(f'[cx46j:standard:{dataset}] {idx}/{len(files)}', flush=True)
        rows.append({
            'dataset': dataset,
            'num_cases': int(len(files)),
            'max_abs_field_diff': float(max(diffs) if diffs else 0.0),
            'mean_abs_field_diff': float(np.mean(diffs) if diffs else 0.0),
        })
    return rows


def _choose_params(dev_summary_path: Path, mod) -> Any:
    rows = json.loads(dev_summary_path.read_text(encoding='utf-8'))
    preferred = [row for row in rows if float(row['time_gain_vs_cx34']) > 0.0 and float(row['time_gain_vs_nowt']) > 0.0]
    if preferred:
        chosen = sorted(preferred, key=lambda row: (float(row['time_gain_vs_cx34']), float(row['time_gain_vs_nowt'])), reverse=True)[0]
    else:
        chosen = sorted(rows, key=lambda row: (float(row['time_gain_vs_cx34']), float(row['time_gain_vs_nowt'])), reverse=True)[0]
    return mod.CX46JRRCParams(**chosen['params']), chosen


def main() -> None:
    args = parse_args()
    args.outputs_root.mkdir(parents=True, exist_ok=True)
    args.reports_root.mkdir(parents=True, exist_ok=True)

    mod = importlib.import_module('rs_cx46.cx46_j_rrc')
    base_mod = importlib.import_module('rs_cx34.cx34_a_msr')
    ref_mod = importlib.import_module('rs_cx46.cx46_f_rbcc')

    predictor = NeuralHeuristicPredictor(args.ours_checkpoint, device=args.device, gaussian_sigma=2.5)
    cfg = CXGlobalConfig()
    train_rows = _read_split_rows(args.split_root / 'calib_train.csv')
    val_rows = _read_split_rows(args.split_root / 'calib_val.csv')
    train_files = [Path(r['path']) for r in train_rows]
    val_files = [Path(r['path']) for r in val_rows]
    public_files = sorted(args.parasol_root.glob('sample_*.npz'))
    train_assets = load_nonholonomic_assets(train_files, predictor, cfg, int(args.dev_cap), tag='cx46j:public-train')
    val_contexts = load_nonholonomic_contexts(val_files, predictor, cfg, tag='cx46j:public-val')
    public_contexts = load_nonholonomic_contexts(public_files, predictor, cfg, tag='cx46j:public')

    base_params = base_mod.CX34AMSRParams(**json.loads(Path('outputs/rs_p0cx34_a_pilot_v1/chosen.json').read_text(encoding='utf-8'))['params'])
    ref_params = ref_mod.CX46FRBCCParams(**json.loads(Path('outputs/rs_p0cx46_f_rbcc_v1/chosen.json').read_text(encoding='utf-8'))['params'])
    params_obj, dev_choice = _choose_params(args.dev_summary, mod)

    base_memory = base_mod.fit_variant(train_assets, val_contexts, predictor, cfg, base_params, args.outputs_root / 'base_fit', args.device, None)
    ref_memory = ref_mod.fit_variant(train_assets, val_contexts, predictor, cfg, ref_params, args.outputs_root / 'ref_fit', args.device, None)
    memory = mod.fit_variant(train_assets, val_contexts, predictor, cfg, params_obj, args.outputs_root / 'fit', args.device, None)

    rows = _eval_cx3(public_contexts, int(args.exp4_cap))
    rows.extend(_eval_variant(base_mod, base_memory, base_params, predictor, cfg, public_contexts, int(args.exp4_cap), args.device, 'CX34-A (Full)'))
    rows.extend(_eval_variant(ref_mod, ref_memory, ref_params, predictor, cfg, public_contexts, int(args.exp4_cap), args.device, 'CX46-F (Full)'))
    rows.extend(_eval_variant(mod, memory, params_obj, predictor, cfg, public_contexts, int(args.exp4_cap), args.device, 'CX46-J (Full)'))
    for spec in mod.ablation_specs():
        rows.extend(_eval_variant(mod, memory, params_obj, predictor, cfg, public_contexts, int(args.exp4_cap), args.device, f"CX46-J ({spec['name']})", ablation=spec))
    _write_csv(args.outputs_root / 'public_case_rows.csv', rows)

    summary = _summary(rows, ('dataset', 'method'))
    delta_vs_cx3 = _delta(summary, ('dataset',), 'CX3-D')
    delta_vs_cx34 = _delta(summary, ('dataset',), 'CX34-A (Full)')
    delta_vs_cx46f = _delta(summary, ('dataset',), 'CX46-F (Full)')
    family_vs_cx34 = _family_delta(rows, 'CX34-A (Full)')
    _write_csv(args.outputs_root / 'public_summary.csv', summary)
    _write_csv(args.outputs_root / 'public_delta_vs_cx3.csv', delta_vs_cx3)
    _write_csv(args.outputs_root / 'public_delta_vs_cx34.csv', delta_vs_cx34)
    _write_csv(args.outputs_root / 'public_delta_vs_cx46f.csv', delta_vs_cx46f)
    _write_csv(args.outputs_root / 'public_family_delta_vs_cx34.csv', family_vs_cx34)

    std = _standard_audit(mod, memory, params_obj, predictor, args.benchmark_root, int(args.max_mp_cases), int(args.max_csm_cases))
    _write_csv(args.outputs_root / 'standard_field_audit.csv', std)
    (args.outputs_root / 'chosen.json').write_text(
        json.dumps(
            {
                'variant': 'CX46-J',
                'params': params_obj.__dict__,
                'dev_choice': dev_choice,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )
    write_inputs_sha256([args.ours_checkpoint, args.split_root / 'calib_train.csv', args.split_root / 'calib_val.csv', args.dev_summary] + train_files + val_files + public_files, args.outputs_root / 'inputs_sha256.json')

    lines = [
        '# CX46-J Public V1',
        '',
        '- protocol: public validation for review-credit scheduler on top of `CX46-F`; candidate selected from dev-summary requiring positive gain vs `CX34-A` and `No-Witness-Transfer` when available',
        f"- chosen params: `{params_obj.__dict__}`",
        f"- dev choice: `{dev_choice}`",
        f"- output root: `{args.outputs_root}`",
        '',
        '## Public vs `CX3-D`',
    ]
    for row in delta_vs_cx3:
        lines.append(f"- `{row['method']}`: success_delta_pp=`{float(row['success_delta_pp']):.3f}`, exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`")
    lines += ['', '## Public vs `CX34-A (Full)`']
    for row in delta_vs_cx34:
        lines.append(f"- `{row['method']}`: success_delta_pp=`{float(row['success_delta_pp']):.3f}`, exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`")
    lines += ['', '## Public vs `CX46-F (Full)`']
    for row in delta_vs_cx46f:
        lines.append(f"- `{row['method']}`: success_delta_pp=`{float(row['success_delta_pp']):.3f}`, exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`")
    lines += ['', '## Public Family Breakdown vs `CX34-A (Full)`']
    for row in family_vs_cx34:
        lines.append(f"- `{row['scenario']}` / `{row['method']}`: exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`")
    lines += ['', '## Standard Support Audit']
    for row in std:
        lines.append(f"- `{row['dataset']}`: num_cases=`{row['num_cases']}`, max_abs_field_diff=`{float(row['max_abs_field_diff']):.6f}`, mean_abs_field_diff=`{float(row['mean_abs_field_diff']):.6f}`")
    (args.reports_root / 'rs_p0cx46_j_public_v1.md').write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    main()
