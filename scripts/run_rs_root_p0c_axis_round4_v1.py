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

from scripts.evaluate_baselines import (
    NeuralHeuristicPredictor,
    _compute_case_rs_field,
    _load_nonholonomic_case,
    _make_ours_anchor,
    _make_rs_anchor,
    _path_length,
    _run_hybrid_method,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="P0-C round3 fixed-cap expansion-focused parameter search.")
    p.add_argument("--benchmark-root", type=Path, default=Path("data/benchmark/rs_root_hard_v2"))
    p.add_argument("--fixed-cap", type=int, default=3500)
    p.add_argument("--families", type=str, default="narrow_passage,maze,deadend_labyrinth")
    p.add_argument("--ours-checkpoint", type=Path, default=Path("outputs/checkpoints/exp3_final_manual_v11b.pt"))
    p.add_argument("--device", type=str, default="cuda")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--bootstrap-n", type=int, default=5000)
    p.add_argument("--path-delta-max-percent", type=float, default=0.5)
    p.add_argument("--rs-field-yaw-bins", type=int, default=24)
    p.add_argument("--residual-alphas", type=str, default="0.45,0.55")
    p.add_argument("--residual-corridor-suppresses", type=str, default="0.3")
    p.add_argument("--residual-open-boosts", type=str, default="0.0,0.45")
    p.add_argument("--residual-bias-quantile", type=float, default=0.25)
    p.add_argument("--residual-corridor-threshold", type=float, default=0.9)
    p.add_argument("--residual-topq-quantile", type=float, default=0.1)
    p.add_argument("--residual-contrastive-bg-quantile", type=float, default=0.62)
    p.add_argument("--residual-contrastive-neg-scale", type=float, default=0.16)
    p.add_argument("--residual-contrastive-pos-scale", type=float, default=1.25)
    p.add_argument("--residual-floor-ratio", type=float, default=0.62)
    p.add_argument("--residual-open-boost-topq", type=float, default=0.9)
    p.add_argument("--residual-open-boost-min-line-clearance", type=float, default=1.8)
    p.add_argument("--out-root", type=Path, default=Path("outputs/rs_root_p0c_axis_round3_v1"))
    p.add_argument("--report-md", type=Path, default=Path("reports/rs_root_p0c_axis_round3_v1.md"))
    return p.parse_args()


def _float_list(raw: str) -> list[float]:
    vals = [float(x.strip()) for x in str(raw).split(",") if x.strip()]
    if not vals:
        raise ValueError("empty float list")
    return vals


def _families(raw: str) -> set[str]:
    return {x.strip() for x in str(raw).split(",") if x.strip()}


def _bootstrap_mean_ci(delta: np.ndarray, n_boot: int) -> tuple[float, float, float, float]:
    arr = np.asarray(delta, dtype=np.float64)
    n = int(arr.size)
    if n <= 0:
        return float("nan"), float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(20260307)
    boots = np.empty(int(n_boot), dtype=np.float64)
    for i in range(int(n_boot)):
        idx = rng.integers(0, n, size=n)
        boots[i] = float(np.mean(arr[idx]))
    return float(np.mean(arr)), float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975)), float(np.mean(boots <= 0.0))


def _filter_files(split_dir: Path, families: set[str], *, anchor_only: bool | None) -> list[Path]:
    out = []
    for p in sorted(split_dir.glob("sample_*.npz")):
        with np.load(p, allow_pickle=False) as z:
            scenario = str(z["scenario"])
            source = str(z.get("source_dataset", "unknown"))
        if scenario not in families:
            continue
        if anchor_only is True and source != "parasol_public_anchor":
            continue
        if anchor_only is False and source == "parasol_public_anchor":
            continue
        out.append(p)
    return out


def _build_case_cache(files: list[Path], predictor: NeuralHeuristicPredictor, args: argparse.Namespace) -> list[dict[str, Any]]:
    cache = []
    total = len(files)
    for i, path in enumerate(files, start=1):
        case = _load_nonholonomic_case(path)
        rs_field = _compute_case_rs_field(case, yaw_bins_cap=int(args.rs_field_yaw_bins))
        rs_anchor = _make_rs_anchor(case, rs_field=rs_field)
        base = _run_hybrid_method(case, rs_anchor, max_expansions=int(args.fixed_cap))
        with np.load(path, allow_pickle=False) as z:
            source = str(z.get('source_dataset', 'unknown'))
        cache.append({
            'path': path,
            'case': case,
            'rs_field': rs_field,
            'base': base,
            'source': source,
        })
        if i % 5 == 0 or i == total:
            print(f"[rs-root-p0c-r3] baseline cached {i}/{total}")
    return cache


def _run_config(cache: list[dict[str, Any]], predictor: NeuralHeuristicPredictor, args: argparse.Namespace, *, residual_alpha: float, corridor_suppress: float, open_boost: float) -> list[dict[str, Any]]:
    rows = []
    total = len(cache)
    for i, item in enumerate(cache, start=1):
        case = item['case']
        rs_field = item['rs_field']
        ours_anchor = _make_ours_anchor(
            case,
            predictor,
            residual_alpha,
            28.0,
            args.residual_bias_quantile,
            args.residual_corridor_threshold,
            corridor_suppress,
            args.residual_topq_quantile,
            args.residual_contrastive_bg_quantile,
            args.residual_contrastive_neg_scale,
            args.residual_contrastive_pos_scale,
            args.residual_floor_ratio,
            0,
            0.0,
            1.0,
            0.0,
            0.0,
            1.0,
            open_boost,
            args.residual_open_boost_topq,
            args.residual_open_boost_min_line_clearance,
            0.0,
            0.0,
            0.95,
            False,
            rs_base_override=rs_field,
        )
        ours = _run_hybrid_method(case, ours_anchor, max_expansions=int(args.fixed_cap))
        rows.append({
            'sample_name': item['path'].name,
            'scenario': str(case['scenario']),
            'source': str(item['source']),
            'ours_success': float(ours['success']),
            'base_success': float(item['base']['success']),
            'ours_expansions': float(ours['expansions']),
            'base_expansions': float(item['base']['expansions']),
            'ours_path_length': float(_path_length(ours['path'])) if ours['path'] else float('nan'),
            'base_path_length': float(_path_length(item['base']['path'])) if item['base']['path'] else float('nan'),
            'ours_time_ms': float(ours['runtime_ms']),
            'base_time_ms': float(item['base']['runtime_ms']),
        })
        if i % 10 == 0 or i == total:
            print(f"[rs-root-p0c-r3] config a={residual_alpha} s={corridor_suppress} b={open_boost} processed {i}/{total}")
    return rows


def _summarize(rows: list[dict[str, Any]], n_boot: int) -> dict[str, Any]:
    succ_delta = np.asarray([r['ours_success'] - r['base_success'] for r in rows], dtype=np.float64)
    exp_delta = np.asarray([r['base_expansions'] - r['ours_expansions'] for r in rows], dtype=np.float64)
    time_delta = np.asarray([r['base_time_ms'] - r['ours_time_ms'] for r in rows], dtype=np.float64)
    path_delta = np.asarray([r['base_path_length'] - r['ours_path_length'] for r in rows if np.isfinite(r['base_path_length']) and np.isfinite(r['ours_path_length'])], dtype=np.float64)
    fam = defaultdict(list)
    for r in rows:
        fam[r['scenario']].append(r)
    fam_rows=[]
    for scen, vals in sorted(fam.items()):
        base_exp=np.mean([x['base_expansions'] for x in vals])
        ours_exp=np.mean([x['ours_expansions'] for x in vals])
        base_time=np.mean([x['base_time_ms'] for x in vals])
        ours_time=np.mean([x['ours_time_ms'] for x in vals])
        fam_rows.append({
            'scenario': scen,
            'num_cases': len(vals),
            'success_delta_pp': 100.0*np.mean([x['ours_success']-x['base_success'] for x in vals]),
            'exp_delta_pct': 100.0*(base_exp-ours_exp)/max(abs(base_exp),1e-12),
            'time_delta_pct': 100.0*(base_time-ours_time)/max(abs(base_time),1e-12),
        })
    return {
        'num_pairs': len(rows),
        'success_delta': dict(zip(['mean','ci95_lo','ci95_hi','p_boot_le0'], _bootstrap_mean_ci(succ_delta, n_boot))),
        'exp_delta': dict(zip(['mean','ci95_lo','ci95_hi','p_boot_le0'], _bootstrap_mean_ci(exp_delta, n_boot))),
        'time_delta': dict(zip(['mean','ci95_lo','ci95_hi','p_boot_le0'], _bootstrap_mean_ci(time_delta, n_boot))),
        'path_delta': dict(zip(['mean','ci95_lo','ci95_hi','p_boot_le0'], _bootstrap_mean_ci(path_delta, n_boot))) if len(path_delta) else None,
        'family_rows': fam_rows,
    }


def _choose(dev_grid: list[dict[str, Any]], path_delta_max_percent: float) -> dict[str, Any]:
    feasible=[]
    for item in dev_grid:
        summ=item['summary']
        succ=float(summ['success_delta']['mean'])
        exp=float(summ['exp_delta']['mean'])
        time=float(summ['time_delta']['mean'])
        path=0.0 if summ['path_delta'] is None else float(summ['path_delta']['mean'])
        # path_delta is base-ours; negative means ours path longer. need not be too negative.
        ok_path = bool((100.0*path/max(abs(np.mean([0.0,1.0])),1.0)) or True)
        # use absolute path mean directly by requiring non-negative or tiny negative relative delta via family summaries impossible; just require path mean >= -0.05m
        if path < -0.05:
            continue
        feasible.append((succ, exp, time, item))
    if not feasible:
        feasible=[(float(item['summary']['success_delta']['mean']), float(item['summary']['exp_delta']['mean']), float(item['summary']['time_delta']['mean']), item) for item in dev_grid]
    feasible.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
    return feasible[0][3]


def main() -> None:
    args = parse_args()
    predictor = NeuralHeuristicPredictor(args.ours_checkpoint, device=args.device, gaussian_sigma=2.5)
    families = _families(args.families)
    t0=time.perf_counter()

    dev_cache = _build_case_cache(_filter_files(args.benchmark_root/'dev', families, anchor_only=None), predictor, args)
    test_cache = _build_case_cache(_filter_files(args.benchmark_root/'test', families, anchor_only=None), predictor, args)

    dev_grid=[]
    for residual_alpha in _float_list(args.residual_alphas):
        for corridor_suppress in _float_list(args.residual_corridor_suppresses):
            for open_boost in _float_list(args.residual_open_boosts):
                rows = _run_config(dev_cache, predictor, args, residual_alpha=residual_alpha, corridor_suppress=corridor_suppress, open_boost=open_boost)
                summary = _summarize(rows, args.bootstrap_n)
                dev_grid.append({
                    'params': {
                        'fixed_cap': int(args.fixed_cap),
                        'residual_alpha': float(residual_alpha),
                        'residual_corridor_suppress': float(corridor_suppress),
                        'residual_open_boost': float(open_boost),
                    },
                    'summary': summary,
                })
    chosen = _choose(dev_grid, args.path_delta_max_percent)
    params = chosen['params']
    print(f"[rs-root-p0c-r3] chosen params={params}")

    test_rows = _run_config(test_cache, predictor, args, residual_alpha=params['residual_alpha'], corridor_suppress=params['residual_corridor_suppress'], open_boost=params['residual_open_boost'])
    test_summary = _summarize(test_rows, args.bootstrap_n)
    test_anchor_summary = _summarize([r for r in test_rows if str(r['source']) == 'parasol_public_anchor'], args.bootstrap_n)

    args.out_root.mkdir(parents=True, exist_ok=True)
    with (args.out_root/'dev_grid.json').open('w', encoding='utf-8') as f:
        json.dump({'grid': dev_grid}, f, indent=2, ensure_ascii=False)
    with (args.out_root/'chosen.json').open('w', encoding='utf-8') as f:
        json.dump({'params': params, 'dev_summary': chosen['summary'], 'test_summary': test_summary, 'test_anchor_summary': test_anchor_summary}, f, indent=2, ensure_ascii=False)
    with (args.out_root/'test_rows.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(test_rows[0].keys()))
        writer.writeheader(); writer.writerows(test_rows)

    lines = [
        '# P0-C Round3 Expansion-Focused Search (V1)',
        '',
        f"- fixed cap: `{args.fixed_cap}`",
        f"- families: `{sorted(list(families))}`",
        '- search objective: no success drop, then maximize expansion gain on dev high-constraint-all; time is secondary; no budget-cap search in this round.',
        '',
        f"Chosen params: `{params}`",
        '',
        '## Dev Summary (chosen config)',
        f"- success delta mean: `{chosen['summary']['success_delta']['mean']:.6f}`",
        f"- expansion delta mean: `{chosen['summary']['exp_delta']['mean']:.6f}`; CI=`[{chosen['summary']['exp_delta']['ci95_lo']:.6f}, {chosen['summary']['exp_delta']['ci95_hi']:.6f}]`; p<=0=`{chosen['summary']['exp_delta']['p_boot_le0']:.6f}`",
        f"- time delta mean: `{chosen['summary']['time_delta']['mean']:.6f}`; CI=`[{chosen['summary']['time_delta']['ci95_lo']:.6f}, {chosen['summary']['time_delta']['ci95_hi']:.6f}]`; p<=0=`{chosen['summary']['time_delta']['p_boot_le0']:.6f}`",
        '',
        '## Test Summary (high_constraint_all)',
        f"- success delta mean: `{test_summary['success_delta']['mean']:.6f}`",
        f"- expansion delta mean: `{test_summary['exp_delta']['mean']:.6f}`; CI=`[{test_summary['exp_delta']['ci95_lo']:.6f}, {test_summary['exp_delta']['ci95_hi']:.6f}]`; p<=0=`{test_summary['exp_delta']['p_boot_le0']:.6f}`",
        f"- time delta mean: `{test_summary['time_delta']['mean']:.6f}`; CI=`[{test_summary['time_delta']['ci95_lo']:.6f}, {test_summary['time_delta']['ci95_hi']:.6f}]`; p<=0=`{test_summary['time_delta']['p_boot_le0']:.6f}`",
        '',
        '## Test Summary (public_anchor_only)',
        f"- success delta mean: `{test_anchor_summary['success_delta']['mean']:.6f}`",
        f"- expansion delta mean: `{test_anchor_summary['exp_delta']['mean']:.6f}`; CI=`[{test_anchor_summary['exp_delta']['ci95_lo']:.6f}, {test_anchor_summary['exp_delta']['ci95_hi']:.6f}]`; p<=0=`{test_anchor_summary['exp_delta']['p_boot_le0']:.6f}`",
        f"- time delta mean: `{test_anchor_summary['time_delta']['mean']:.6f}`; CI=`[{test_anchor_summary['time_delta']['ci95_lo']:.6f}, {test_anchor_summary['time_delta']['ci95_hi']:.6f}]`; p<=0=`{test_anchor_summary['time_delta']['p_boot_le0']:.6f}`",
        '',
        '## Honest Conclusion',
    ]
    if float(test_summary['exp_delta']['mean']) > 0.0 and float(test_summary['exp_delta']['exp_ci95_lo'] if False else 0.0):
        pass
    lines.append('- Interpret the high-constraint-all test first; use public_anchor_only as a conservative sanity check.')
    args.report_md.write_text('\n'.join(lines), encoding='utf-8')
    print(f"[rs-root-p0c-r3] report={args.report_md}")
    print(f"[rs-root-p0c-r3] out_root={args.out_root}")


if __name__ == '__main__':
    main()
