from __future__ import annotations

import argparse
import csv
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from rs_macro_rescue.network.inference import NeuralHeuristicPredictor
from rs_macro_rescue.stack.base import CXGlobalConfig
from rs_macro_rescue.mainline import macro_rescue as main_mod
from rs_macro_rescue.mainline.mainline import (
    CURRENT_RS_MAINLINE_CANONICAL_DEVICE,
    DEFAULT_EXTERNAL_EVAL_OUTPUT_ROOT,
    DEFAULT_EXTERNAL_EVAL_REPORT,
    load_current_mainline_params,
)
from rs_macro_rescue.stack.nonholonomic import load_nonholonomic_assets, load_nonholonomic_contexts, run_hybrid_with_policy, write_inputs_sha256


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Run the retained RS + Macro Rescue mainline on external datasets.')
    p.add_argument('--benchmark-root', type=Path, default=Path('data/benchmark'))
    p.add_argument('--datasets', type=str, default='parasol_narrow,mp,csm')
    p.add_argument('--calib-dataset', type=str, default='mp')
    p.add_argument('--calib-train-count', type=int, default=24)
    p.add_argument('--calib-val-count', type=int, default=8)
    p.add_argument('--max-cases', type=int, default=0)
    p.add_argument('--ours-checkpoint', type=Path, required=True)
    p.add_argument('--device', type=str, default=CURRENT_RS_MAINLINE_CANONICAL_DEVICE)
    p.add_argument('--max-expansions', type=int, default=20000)
    p.add_argument('--outputs-root', type=Path, default=DEFAULT_EXTERNAL_EVAL_OUTPUT_ROOT)
    p.add_argument('--report-md', type=Path, default=DEFAULT_EXTERNAL_EVAL_REPORT)
    return p.parse_args()


def _dataset_names(raw: str) -> list[str]:
    return [name.strip() for name in str(raw).split(',') if name.strip()]


def _limited(files: list[Path], limit: int) -> list[Path]:
    if int(limit) <= 0:
        return files
    return files[: int(limit)]


def _path_len(plan) -> float:
    path = np.asarray(getattr(plan, 'path', []), dtype=np.float32)
    if path.ndim != 2 or path.shape[0] < 2:
        return float('nan')
    xy = path[:, :2]
    return float(np.sum(np.linalg.norm(xy[1:] - xy[:-1], axis=1)))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
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
    out: list[dict[str, Any]] = []
    for key, group in sorted(grouped.items()):
        item = {k: key[i] for i, k in enumerate(keys)}
        item.update(
            {
                'num_cases': len(group),
                'success_rate': float(np.mean([float(r['success']) for r in group])),
                'avg_expansions': float(np.mean([float(r['expansions']) for r in group])),
                'avg_time_ms': float(np.mean([float(r['time_ms']) for r in group])),
                'avg_path_length': float(np.nanmean([float(r['path_length']) for r in group])),
            }
        )
        out.append(item)
    return out


def _delta(summary_rows: list[dict[str, Any]], group_keys: tuple[str, ...], baseline_method: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in summary_rows:
        grouped[tuple(row[k] for k in group_keys)][str(row['method'])] = row
    out: list[dict[str, Any]] = []
    for group, methods in sorted(grouped.items()):
        base = methods.get(baseline_method)
        if base is None:
            continue
        for method, row in methods.items():
            if method == baseline_method:
                continue
            item = {k: group[i] for i, k in enumerate(group_keys)}
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


def _eval_baseline(assets: list[dict[str, Any]], cap: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    total = len(assets)
    for idx, asset in enumerate(assets, start=1):
        plan = run_hybrid_with_policy(asset['case'], asset['field'], int(cap), successor_policy=None, record_expanded=False)
        rows.append(
            {
                'dataset': str(asset['dataset']),
                'sample_name': str(asset['path'].name),
                'scenario': str(asset['case'].get('scenario', 'unknown')),
                'method': 'CX3-D',
                'success': float(plan.success),
                'expansions': float(plan.expansions),
                'time_ms': float(plan.runtime_ms),
                'path_length': float(_path_len(plan)),
            }
        )
        if idx % 25 == 0 or idx == total:
            print(f"[CX3-D:{asset['dataset']}] {idx}/{total}", flush=True)
    return rows


def _eval_mainline(memory: dict[str, Any], params_obj, predictor, cfg: CXGlobalConfig, assets: list[dict[str, Any]], cap: int, device: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    total = len(assets)
    for idx, asset in enumerate(assets, start=1):
        field = main_mod.build_nonholonomic_field(asset['case'], predictor, cfg, params_obj, memory)
        bundle = asset['case'].get('_cx21_bundle', asset['bundle'])
        t0 = time.perf_counter()
        policy = main_mod.make_policy(memory, params_obj, asset['case'], bundle, field, device, ablation=None)
        prep_ms = (time.perf_counter() - t0) * 1000.0
        plan = run_hybrid_with_policy(asset['case'], field, int(cap), successor_policy=policy, record_expanded=False)
        rows.append(
            {
                'dataset': str(asset['dataset']),
                'sample_name': str(asset['path'].name),
                'scenario': str(asset['case'].get('scenario', 'unknown')),
                'method': 'RS-MacroRescue',
                'success': float(plan.success),
                'expansions': float(plan.expansions),
                'time_ms': float(plan.runtime_ms + prep_ms),
                'path_length': float(_path_len(plan)),
            }
        )
        if idx % 25 == 0 or idx == total:
            print(f"[RS-MacroRescue:{asset['dataset']}] {idx}/{total}", flush=True)
    return rows


def main() -> None:
    args = parse_args()
    if not args.ours_checkpoint.exists():
        raise FileNotFoundError(f'checkpoint not found: {args.ours_checkpoint}')

    args.outputs_root.mkdir(parents=True, exist_ok=True)
    args.report_md.parent.mkdir(parents=True, exist_ok=True)

    predictor = NeuralHeuristicPredictor(args.ours_checkpoint, device=args.device, gaussian_sigma=2.5)
    cfg = CXGlobalConfig()
    params_obj = load_current_mainline_params()

    calib_files = sorted((args.benchmark_root / args.calib_dataset / 'train').glob('sample_*.npz'))
    if not calib_files:
        raise RuntimeError(f'empty calibration split: {args.benchmark_root / args.calib_dataset / "train"}')
    train_files = calib_files[: int(max(args.calib_train_count, 1))]
    val_files = calib_files[int(max(args.calib_train_count, 1)) : int(max(args.calib_train_count, 1)) + int(max(args.calib_val_count, 0))]

    train_assets = load_nonholonomic_assets(train_files, predictor, cfg, int(args.max_expansions), tag='macro_rescue:calib-train')
    val_contexts = load_nonholonomic_contexts(val_files, predictor, cfg, tag='macro_rescue:calib-val') if val_files else []
    memory = main_mod.fit_variant(train_assets, val_contexts, predictor, cfg, params_obj, args.outputs_root / 'fit', args.device)

    eval_assets: list[dict[str, Any]] = []
    for dataset in _dataset_names(args.datasets):
        files = _limited(sorted((args.benchmark_root / dataset / 'test').glob('sample_*.npz')), int(args.max_cases))
        contexts = load_nonholonomic_contexts(files, predictor, cfg, tag=f'macro_rescue:{dataset}:test')
        for ctx in contexts:
            ctx['dataset'] = dataset
        eval_assets.extend(contexts)

    rows = _eval_baseline(eval_assets, int(args.max_expansions))
    rows.extend(_eval_mainline(memory, params_obj, predictor, cfg, eval_assets, int(args.max_expansions), args.device))

    summary_rows = _summary(rows, ('dataset', 'method'))
    delta_rows = _delta(summary_rows, ('dataset',), baseline_method='CX3-D')
    family_rows = _delta(_summary(rows, ('dataset', 'scenario', 'method')), ('dataset', 'scenario'), baseline_method='CX3-D')

    _write_csv(args.outputs_root / 'case_rows.csv', rows)
    _write_csv(args.outputs_root / 'summary.csv', summary_rows)
    _write_csv(args.outputs_root / 'delta_vs_cx3.csv', delta_rows)
    _write_csv(args.outputs_root / 'family_delta_vs_cx3.csv', family_rows)
    (args.outputs_root / 'mainline_params.json').write_text(json.dumps(params_obj.__dict__, indent=2, ensure_ascii=False), encoding='utf-8')
    write_inputs_sha256([args.ours_checkpoint] + train_files + val_files + [asset['path'] for asset in eval_assets], args.outputs_root / 'inputs_sha256.json')

    lines = [
        '# RS + Macro Rescue External Eval',
        '',
        '- retained mainline: `RS + Macro Rescue / Subtype-Specific Macro Rescue`',
        f'- external datasets: `{", ".join(_dataset_names(args.datasets))}`',
        f'- calibration source: `{args.calib_dataset}/train`',
        f'- checkpoint: `{args.ours_checkpoint}`',
        f'- params: `{params_obj.__dict__}`',
        '',
        '## Overall vs CX3-D',
    ]
    for row in delta_rows:
        lines.append(
            f"- `{row['dataset']}` / `{row['method']}`: "
            f"success_delta_pp=`{float(row['success_delta_pp']):.3f}`, "
            f"exp_delta=`{float(row['exp_delta']):.3f}`, "
            f"mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`, "
            f"path_delta=`{float(row['path_delta']):.3f}`"
        )
    args.report_md.write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    main()
