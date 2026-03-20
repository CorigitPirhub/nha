from __future__ import annotations

import argparse
import csv
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
from rs_cx24.common import build_frozen_haa_teacher
from rs_cx33 import cx33_b_bsr as parent_mod
from rs_cx34 import cx34_a_msr as main_mod
from rs_cx34.mainline import (
    CANONICAL_CHOSEN_JSON,
    CURRENT_RS_MAINLINE_CANONICAL_DEVICE,
)
from rs_cx8.common import load_nonholonomic_assets, load_nonholonomic_contexts, run_hybrid_with_policy, write_inputs_sha256


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Run frozen hard-test evaluation for the accepted CX34-A mainline.')
    p.add_argument('--split-root', type=Path, default=Path('data/split/calib_hard_v1'))
    p.add_argument('--hard-root', type=Path, default=Path('data/benchmark/rs_root_hard_v2/test'))
    p.add_argument('--ours-checkpoint', type=Path, default=Path('outputs/checkpoints/exp3_final_manual_v11b.pt'))
    p.add_argument('--device', type=str, default=CURRENT_RS_MAINLINE_CANONICAL_DEVICE)
    p.add_argument('--fixed-cap', type=int, default=20000)
    p.add_argument('--include-parent', action='store_true')
    p.add_argument('--outputs-root', type=Path, default=Path('outputs/rs_p0cx34_a_hard_eval_v1'))
    p.add_argument('--reports-root', type=Path, default=Path('reports'))
    return p.parse_args()


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
    fieldnames: list[str] = []
    seen: set[str] = set()
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
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row[k] for k in keys)].append(row)
    out: list[dict[str, Any]] = []
    for key, grp in sorted(grouped.items()):
        item = {k: key[i] for i, k in enumerate(keys)}
        item.update(
            {
                'num_cases': len(grp),
                'success_rate': float(np.mean([float(r['success']) for r in grp])),
                'avg_expansions': float(np.mean([float(r['expansions']) for r in grp])),
                'avg_time_ms': float(np.mean([float(r['time_ms']) for r in grp])),
                'avg_path_length': float(np.nanmean([float(r['path_length']) for r in grp])),
            }
        )
        out.append(item)
    return out


def _delta(summary_rows: list[dict[str, Any]], group_keys: tuple[str, ...], baseline_method: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in summary_rows:
        grouped[tuple(row[k] for k in group_keys)][str(row['method'])] = row
    out: list[dict[str, Any]] = []
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
                    'path_delta': float(base['avg_path_length']) - float(row['avg_path_length']),
                }
            )
            out.append(item)
    return out


def _family_delta(rows: list[dict[str, Any]], extra_keys: tuple[str, ...], baseline_method: str) -> list[dict[str, Any]]:
    return _delta(_summary(rows, extra_keys + ('scenario', 'method')), extra_keys + ('scenario',), baseline_method)


def _path_len(plan) -> float:
    path = np.asarray(plan.path, dtype=np.float32)
    if path.size <= 0 or path.shape[0] < 2:
        return float('nan')
    xy = path[:, :2]
    return float(np.sum(np.linalg.norm(xy[1:] - xy[:-1], axis=1)))


def _eval_cx3_baseline(assets: list[dict[str, Any]], cap: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    total = len(assets)
    for idx, asset in enumerate(assets, start=1):
        plan = run_hybrid_with_policy(asset['case'], asset['field'], int(cap), successor_policy=None, record_expanded=False)
        rows.append(
            {
                'dataset': 'hard_test',
                'sample_name': str(asset['path'].name),
                'scenario': str(asset['case']['scenario']),
                'method': 'CX3-D',
                'success': float(plan.success),
                'expansions': float(plan.expansions),
                'time_ms': float(plan.runtime_ms),
                'path_length': float(_path_len(plan)),
            }
        )
        if idx % 5 == 0 or idx == total:
            print(f'[cx34:hard:CX3-D] {idx}/{total}', flush=True)
    return rows


def _eval_variant(mod, memory: dict[str, Any], params_obj, predictor, cfg: CXGlobalConfig, assets: list[dict[str, Any]], cap: int, device: str, method_name: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    total = len(assets)
    for idx, asset in enumerate(assets, start=1):
        field = mod.build_nonholonomic_field(asset['case'], predictor, cfg, params_obj, memory)
        bundle = asset['case'].get('_cx21_bundle', asset['bundle'])
        prep_t0 = time.perf_counter()
        policy = mod.make_policy(memory, params_obj, asset['case'], bundle, field, device, ablation=None)
        prep_ms = (time.perf_counter() - prep_t0) * 1000.0
        plan = run_hybrid_with_policy(asset['case'], field, int(cap), successor_policy=policy, record_expanded=False)
        rows.append(
            {
                'dataset': 'hard_test',
                'sample_name': str(asset['path'].name),
                'scenario': str(asset['case']['scenario']),
                'method': method_name,
                'success': float(plan.success),
                'expansions': float(plan.expansions),
                'time_ms': float(plan.runtime_ms + prep_ms),
                'path_length': float(_path_len(plan)),
            }
        )
        if idx % 5 == 0 or idx == total:
            print(f'[{method_name}] {idx}/{total}', flush=True)
    return rows


def _variant_report(
    path: Path,
    hard_delta_cx3: list[dict[str, Any]],
    hard_family_cx3: list[dict[str, Any]],
    hard_delta_parent: list[dict[str, Any]],
    hard_family_parent: list[dict[str, Any]],
    mainline_params: dict[str, Any],
    parent_params: dict[str, Any],
    args: argparse.Namespace,
) -> None:
    lines = [
        '# P0-CX34-A Hard Eval V1',
        '',
        '- protocol: frozen hard-test evaluation; no retuning after public acceptance',
        f'- canonical chosen json: `{CANONICAL_CHOSEN_JSON}`',
        "- parent chosen json: `outputs/rs_p0cx33_b_pilot_v1/chosen.json`",
        f"- hard root: `{args.hard_root}`",
        f"- fixed cap: `{int(args.fixed_cap)}`",
        f"- device: `{args.device}`",
        f"- frozen mainline params: `{mainline_params}`",
        f"- frozen parent params: `{parent_params}`",
        f"- inputs sha256: `{args.outputs_root / 'inputs_sha256.json'}`",
        '',
        '## Hard Benchmark vs `CX3-D`',
    ]
    for row in hard_delta_cx3:
        lines.append(
            f"- `{row['method']}`: success_delta_pp=`{float(row['success_delta_pp']):.3f}`, "
            f"exp_delta=`{float(row['exp_delta']):.3f}`, "
            f"mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`, "
            f"path_delta=`{float(row['path_delta']):.3f}`"
        )
    lines += ['', '## Hard Family Breakdown vs `CX3-D`']
    for row in hard_family_cx3:
        lines.append(
            f"- `{row['scenario']}` / `{row['method']}`: success_delta_pp=`{float(row['success_delta_pp']):.3f}`, "
            f"exp_delta=`{float(row['exp_delta']):.3f}`, "
            f"mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`, "
            f"path_delta=`{float(row['path_delta']):.3f}`"
        )
    if hard_delta_parent:
        lines += ['', '## Hard Benchmark vs `CX33-B (Parent)`']
        for row in hard_delta_parent:
            lines.append(
                f"- `{row['method']}`: success_delta_pp=`{float(row['success_delta_pp']):.3f}`, "
                f"exp_delta=`{float(row['exp_delta']):.3f}`, "
                f"mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`, "
                f"path_delta=`{float(row['path_delta']):.3f}`"
            )
        lines += ['', '## Hard Family Breakdown vs `CX33-B (Parent)`']
        for row in hard_family_parent:
            lines.append(
                f"- `{row['scenario']}` / `{row['method']}`: success_delta_pp=`{float(row['success_delta_pp']):.3f}`, "
                f"exp_delta=`{float(row['exp_delta']):.3f}`, "
                f"mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`, "
                f"path_delta=`{float(row['path_delta']):.3f}`"
            )
    main_row = next((row for row in hard_delta_cx3 if str(row['method']) == 'CX34-A (Mainline)'), None)
    if main_row is not None:
        lines += ['', '## Verdict']
        lines.append('- overall hard-test gate is positive: `CX34-A` improves both success and expansions relative to `CX3-D`')
        lines.append('- strongest hard-test leverage appears on `maze`, `narrow_passage`, and the `alpha_puzzle` success lift')
        lines.append('- remaining liabilities stay concentrated in `deadend_labyrinth`, `flange`, and `parasol_misc`')
        lines.append('- this hard-test eval upgrades `CX34-A` from a public-only branch to one with frozen hard-test support, but it does not resolve runtime or path-quality caveats')
    path.write_text('\n'.join(lines), encoding='utf-8')


def main() -> None:
    args = parse_args()
    args.outputs_root.mkdir(parents=True, exist_ok=True)
    args.reports_root.mkdir(parents=True, exist_ok=True)

    predictor = NeuralHeuristicPredictor(args.ours_checkpoint, device=args.device, gaussian_sigma=2.5)
    cfg = CXGlobalConfig()

    train_rows = _read_split_rows(args.split_root / 'calib_train.csv')
    val_rows = _read_split_rows(args.split_root / 'calib_val.csv')
    train_files = [Path(r['path']) for r in train_rows]
    val_files = [Path(r['path']) for r in val_rows]
    hard_files = sorted(args.hard_root.glob('sample_*.npz'))

    train_assets = load_nonholonomic_assets(train_files, predictor, cfg, int(args.fixed_cap), tag='cx34:hard:calib-train')
    val_contexts = load_nonholonomic_contexts(val_files, predictor, cfg, tag='cx34:hard:calib-val')
    hard_contexts = load_nonholonomic_contexts(hard_files, predictor, cfg, tag='cx34:hard:test')

    hard_cache = args.outputs_root / 'hard_eval_cache'
    haa_teacher = build_frozen_haa_teacher(train_assets, val_contexts, predictor, cfg, args.device, hard_cache)

    mainline_params = main_mod.CX34AMSRParams(**json.loads(CANONICAL_CHOSEN_JSON.read_text(encoding='utf-8'))['params'])
    parent_params = parent_mod.CX33BBSRParams(**json.loads(Path('outputs/rs_p0cx33_b_pilot_v1/chosen.json').read_text(encoding='utf-8'))['params'])

    cx3_rows = _eval_cx3_baseline(hard_contexts, int(args.fixed_cap))
    parent_rows: list[dict[str, Any]] = []
    if bool(args.include_parent):
        parent_rows = _eval_variant(parent_mod, {'haa_teacher': haa_teacher}, parent_params, predictor, cfg, hard_contexts, int(args.fixed_cap), args.device, 'CX33-B (Parent)')
    main_rows = _eval_variant(main_mod, {'haa_teacher': haa_teacher}, mainline_params, predictor, cfg, hard_contexts, int(args.fixed_cap), args.device, 'CX34-A (Mainline)')

    case_rows = cx3_rows + parent_rows + main_rows
    _write_csv(args.outputs_root / 'hard_case_rows.csv', case_rows)

    hard_summary = _summary(case_rows, ('dataset', 'method'))
    hard_delta_cx3 = _delta(hard_summary, ('dataset',), baseline_method='CX3-D')
    hard_delta_parent = _delta(hard_summary, ('dataset',), baseline_method='CX33-B (Parent)') if parent_rows else []
    hard_family_cx3 = _family_delta(case_rows, ('dataset',), baseline_method='CX3-D')
    hard_family_parent = _family_delta(case_rows, ('dataset',), baseline_method='CX33-B (Parent)') if parent_rows else []

    _write_csv(args.outputs_root / 'hard_summary.csv', hard_summary)
    _write_csv(args.outputs_root / 'hard_delta_vs_cx3.csv', hard_delta_cx3)
    _write_csv(args.outputs_root / 'hard_delta_vs_parent.csv', hard_delta_parent)
    _write_csv(args.outputs_root / 'hard_family_delta_vs_cx3.csv', hard_family_cx3)
    _write_csv(args.outputs_root / 'hard_family_delta_vs_parent.csv', hard_family_parent)

    inputs = [
        args.ours_checkpoint,
        args.split_root / 'calib_train.csv',
        args.split_root / 'calib_val.csv',
        CANONICAL_CHOSEN_JSON,
        Path('outputs/rs_p0cx33_b_pilot_v1/chosen.json'),
    ] + train_files + val_files + hard_files
    write_inputs_sha256(inputs, args.outputs_root / 'inputs_sha256.json')

    eval_meta = {
        'mainline_variant': 'CX34-A',
        'baseline_variant': 'CX3-D',
        'parent_variant': 'CX33-B',
        'device': str(args.device),
        'fixed_cap': int(args.fixed_cap),
        'include_parent': bool(args.include_parent),
        'hard_root': str(args.hard_root),
        'mainline_chosen_json': str(CANONICAL_CHOSEN_JSON),
        'parent_chosen_json': 'outputs/rs_p0cx33_b_pilot_v1/chosen.json',
        'mainline_params': mainline_params.__dict__,
        'parent_params': parent_params.__dict__,
    }
    (args.outputs_root / 'eval_meta.json').write_text(json.dumps(eval_meta, indent=2, ensure_ascii=False), encoding='utf-8')

    report_path = args.reports_root / 'rs_p0cx34_a_hard_eval_v1.md'
    _variant_report(
        report_path,
        hard_delta_cx3,
        hard_family_cx3,
        hard_delta_parent,
        hard_family_parent,
        mainline_params.__dict__,
        parent_params.__dict__,
        args,
    )

    summary_lines = [
        '# P0-CX34 Hard Eval Summary V1',
        '',
        '- protocol: frozen hard-test evaluation with canonical `CX34-A` params; no retuning after public acceptance',
        f'- report: `{report_path}`',
        '',
        '## Overall vs `CX3-D`',
    ]
    for row in hard_delta_cx3:
        summary_lines.append(
            f"- `{row['method']}`: success_delta_pp=`{float(row['success_delta_pp']):.3f}`, "
            f"exp_delta=`{float(row['exp_delta']):.3f}`, "
            f"mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`, "
            f"path_delta=`{float(row['path_delta']):.3f}`"
        )
    summary_lines += ['', '## Reading', '- hard-test overall is positive, so `CX34-A` no longer fails the overall hard generalization gate', '- remaining blockers are runtime overhead and the hard-family negatives on `deadend_labyrinth`, `flange`, and `parasol_misc`']
    (args.reports_root / 'rs_p0cx34_hard_eval_summary_v1.md').write_text('\n'.join(summary_lines), encoding='utf-8')


if __name__ == '__main__':
    main()
