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


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Run frozen hard-test evaluation for CX44-A.')
    p.add_argument('--split-root', type=Path, default=Path('data/split/calib_hard_v1'))
    p.add_argument('--hard-root', type=Path, default=Path('data/benchmark/rs_root_hard_v2/test'))
    p.add_argument('--ours-checkpoint', type=Path, default=Path('outputs/checkpoints/exp3_final_manual_v11b.pt'))
    p.add_argument('--device', type=str, default='cuda')
    p.add_argument('--fixed-cap', type=int, default=20000)
    p.add_argument('--chosen-json', type=Path, default=Path('outputs/rs_p0cx44_a_pilot_v1/chosen.json'))
    p.add_argument('--parent-chosen-json', type=Path, default=Path('outputs/rs_p0cx34_a_pilot_v1/chosen.json'))
    p.add_argument('--compat-chosen-json', type=Path, default=Path('outputs/rs_p0cx41_b_pilot_v1/chosen.json'))
    p.add_argument('--outputs-root', type=Path, default=Path('outputs/rs_p0cx44_a_hard_eval_v1'))
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
        item.update({'num_cases': len(grp), 'success_rate': float(np.mean([float(r['success']) for r in grp])), 'avg_expansions': float(np.mean([float(r['expansions']) for r in grp])), 'avg_time_ms': float(np.mean([float(r['time_ms']) for r in grp])), 'avg_path_length': float(np.nanmean([float(r['path_length']) for r in grp]))})
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
            item.update({'method': method, 'baseline': baseline_method, 'success_delta_pp': 100.0 * (float(row['success_rate']) - float(base['success_rate'])), 'exp_delta': float(base['avg_expansions']) - float(row['avg_expansions']), 'mean_time_overhead_ratio': (float(row['avg_time_ms']) - float(base['avg_time_ms'])) / max(float(base['avg_time_ms']), 1e-6), 'path_delta': float(base['avg_path_length']) - float(row['avg_path_length'])})
            out.append(item)
    return out


def _family_delta(rows: list[dict[str, Any]], baseline_method: str) -> list[dict[str, Any]]:
    return _delta(_summary(rows, ('dataset', 'scenario', 'method')), ('dataset', 'scenario'), baseline_method)


def _path_len(plan) -> float:
    path = np.asarray(plan.path, dtype=np.float32)
    if path.size <= 0 or path.shape[0] < 2:
        return float('nan')
    xy = path[:, :2]
    return float(np.sum(np.linalg.norm(xy[1:] - xy[:-1], axis=1)))


def _eval_cx3(assets: list[dict[str, Any]], cap: int) -> list[dict[str, Any]]:
    rows = []
    total = len(assets)
    for idx, asset in enumerate(assets, start=1):
        plan = run_hybrid_with_policy(asset['case'], asset['field'], int(cap), successor_policy=None, record_expanded=False)
        rows.append({'dataset': 'hard_test', 'sample_name': str(asset['path'].name), 'scenario': str(asset['case']['scenario']), 'method': 'CX3-D', 'success': float(plan.success), 'expansions': float(plan.expansions), 'time_ms': float(plan.runtime_ms), 'path_length': float(_path_len(plan))})
        if idx % 5 == 0 or idx == total:
            print(f'[cx44a-hard:CX3-D] {idx}/{total}', flush=True)
    return rows


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
        rows.append({'dataset': 'hard_test', 'sample_name': str(asset['path'].name), 'scenario': str(asset['case']['scenario']), 'method': method_name, 'success': float(plan.success), 'expansions': float(plan.expansions), 'time_ms': float(plan.runtime_ms + prep_ms), 'path_length': float(_path_len(plan)), 'witness_hits': float(stats.get('witness_hits', 0.0)), 'witness_store_negative': float(stats.get('witness_store_negative', 0.0)), 'witness_full_reviews': float(stats.get('witness_full_reviews', 0.0))})
        if idx % 5 == 0 or idx == total:
            print(f'[{method_name}] {idx}/{total}', flush=True)
    return rows


def main() -> None:
    args = parse_args()
    args.outputs_root.mkdir(parents=True, exist_ok=True)
    args.reports_root.mkdir(parents=True, exist_ok=True)

    mod = importlib.import_module('rs_cx44.cx44_a_rmrc')
    parent_mod = importlib.import_module('rs_cx34.cx34_a_msr')
    compat_mod = importlib.import_module('rs_cx41.cx41_b_fdr')

    chosen = json.loads(args.chosen_json.read_text(encoding='utf-8'))
    parent_chosen = json.loads(args.parent_chosen_json.read_text(encoding='utf-8'))
    compat_chosen = json.loads(args.compat_chosen_json.read_text(encoding='utf-8'))
    params_obj = mod.CX44ARMRCParams(**chosen['params'])
    parent_params = parent_mod.CX34AMSRParams(**parent_chosen['params'])
    compat_params = compat_mod.CX41BFDRParams(**compat_chosen['params'])

    predictor = NeuralHeuristicPredictor(args.ours_checkpoint, device=args.device, gaussian_sigma=2.5)
    cfg = CXGlobalConfig()
    train_rows = _read_split_rows(args.split_root / 'calib_train.csv')
    val_rows = _read_split_rows(args.split_root / 'calib_val.csv')
    train_files = [Path(r['path']) for r in train_rows]
    val_files = [Path(r['path']) for r in val_rows]
    hard_files = sorted(args.hard_root.glob('sample_*.npz'))
    train_assets = load_nonholonomic_assets(train_files, predictor, cfg, int(args.fixed_cap), tag='cx44a-hard:train')
    val_contexts = load_nonholonomic_contexts(val_files, predictor, cfg, tag='cx44a-hard:val')
    hard_contexts = load_nonholonomic_contexts(hard_files, predictor, cfg, tag='cx44a-hard:test')

    parent_memory = parent_mod.fit_variant(train_assets, val_contexts, predictor, cfg, parent_params, args.outputs_root / 'parent_fit', args.device, None)
    compat_memory = compat_mod.fit_variant(train_assets, val_contexts, predictor, cfg, compat_params, args.outputs_root / 'compat_fit', args.device, None)
    memory = mod.fit_variant(train_assets, val_contexts, predictor, cfg, params_obj, args.outputs_root / 'fit', args.device, None)

    rows = _eval_cx3(hard_contexts, int(args.fixed_cap))
    rows.extend(_eval_variant(parent_mod, parent_memory, parent_params, predictor, cfg, hard_contexts, int(args.fixed_cap), args.device, 'CX34-A (Full)'))
    rows.extend(_eval_variant(compat_mod, compat_memory, compat_params, predictor, cfg, hard_contexts, int(args.fixed_cap), args.device, 'CX41-B (Full)'))
    rows.extend(_eval_variant(mod, memory, params_obj, predictor, cfg, hard_contexts, int(args.fixed_cap), args.device, 'CX44-A (Full)'))
    for spec in mod.ablation_specs():
        rows.extend(_eval_variant(mod, memory, params_obj, predictor, cfg, hard_contexts, int(args.fixed_cap), args.device, f"CX44-A ({spec['name']})", ablation=spec))
    _write_csv(args.outputs_root / 'hard_case_rows.csv', rows)

    summary = _summary(rows, ('dataset', 'method'))
    delta_vs_cx3 = _delta(summary, ('dataset',), 'CX3-D')
    delta_vs_cx34 = _delta(summary, ('dataset',), 'CX34-A (Full)')
    delta_vs_cx41 = _delta(summary, ('dataset',), 'CX41-B (Full)')
    family_vs_cx34 = _family_delta(rows, 'CX34-A (Full)')
    _write_csv(args.outputs_root / 'hard_summary.csv', summary)
    _write_csv(args.outputs_root / 'hard_delta_vs_cx3.csv', delta_vs_cx3)
    _write_csv(args.outputs_root / 'hard_delta_vs_cx34.csv', delta_vs_cx34)
    _write_csv(args.outputs_root / 'hard_delta_vs_cx41.csv', delta_vs_cx41)
    _write_csv(args.outputs_root / 'hard_family_delta_vs_cx34.csv', family_vs_cx34)
    write_inputs_sha256([args.ours_checkpoint, args.chosen_json, args.parent_chosen_json, args.compat_chosen_json, args.split_root / 'calib_train.csv', args.split_root / 'calib_val.csv'] + train_files + val_files + hard_files, args.outputs_root / 'inputs_sha256.json')

    lines = [
        '# P0-CX44-A Hard Eval V1',
        '',
        '- protocol: frozen hard-test evaluation; no retuning after public selection',
        f'- chosen json: `{args.chosen_json}`',
        f'- parent chosen json: `{args.parent_chosen_json}`',
        f'- compat chosen json: `{args.compat_chosen_json}`',
        f'- hard root: `{args.hard_root}`',
        '',
        '## Hard Benchmark vs `CX3-D`',
    ]
    for row in delta_vs_cx3:
        lines.append(f"- `{row['method']}`: success_delta_pp=`{float(row['success_delta_pp']):.3f}`, exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`, path_delta=`{float(row['path_delta']):.3f}`")
    lines += ['', '## Hard Benchmark vs `CX34-A (Full)`']
    for row in delta_vs_cx34:
        lines.append(f"- `{row['method']}`: success_delta_pp=`{float(row['success_delta_pp']):.3f}`, exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`, path_delta=`{float(row['path_delta']):.3f}`")
    lines += ['', '## Hard Benchmark vs `CX41-B (Full)`']
    for row in delta_vs_cx41:
        lines.append(f"- `{row['method']}`: success_delta_pp=`{float(row['success_delta_pp']):.3f}`, exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`, path_delta=`{float(row['path_delta']):.3f}`")
    lines += ['', '## Hard Family Breakdown vs `CX34-A (Full)`']
    for row in family_vs_cx34:
        lines.append(f"- `{row['scenario']}` / `{row['method']}`: success_delta_pp=`{float(row['success_delta_pp']):.3f}`, exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`, path_delta=`{float(row['path_delta']):.3f}`")
    (args.reports_root / 'rs_p0cx44_a_hard_eval_v1.md').write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    main()
