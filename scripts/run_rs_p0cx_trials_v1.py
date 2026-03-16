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
import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baselines.common import load_grid_sample
from network.inference import NeuralHeuristicPredictor
from rs_cx.common import CXGlobalConfig, run_standard_astar
from scripts.evaluate_baselines import (
    _astar_grid,
    _compute_case_rs_field,
    _euclidean_field,
    _load_nonholonomic_case,
    _make_ours_anchor,
    _make_rs_anchor,
    _path_length,
    _resolve_2d_heuristic,
    _run_hybrid_method,
)

CX_MODULES = {
    "CX-A": "rs_cx.cx_a_tube",
    "CX-B": "rs_cx.cx_b_bpf",
    "CX-C": "rs_cx.cx_c_dvp",
    "CX-D": "rs_cx.cx_d_pmf",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run P0-CX RS-grounded base-model innovation trials.")
    p.add_argument("--benchmark-root", type=Path, default=Path("data/benchmark"))
    p.add_argument("--hard-benchmark-root", type=Path, default=Path("data/benchmark/rs_root_hard_v2"))
    p.add_argument("--parasol-root", type=Path, default=Path("data/benchmark/parasol_narrow/test"))
    p.add_argument("--ours-checkpoint", type=Path, default=Path("outputs/checkpoints/exp3_final_manual_v11b.pt"))
    p.add_argument("--device", type=str, default="cuda")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--fixed-cap", type=int, default=3500)
    p.add_argument("--families", type=str, default="narrow_passage,maze,deadend_labyrinth")
    p.add_argument("--variants", type=str, default="CX-A,CX-B,CX-C,CX-D")
    p.add_argument("--max-mp-cases", type=int, default=80)
    p.add_argument("--max-csm-cases", type=int, default=80)
    p.add_argument("--bootstrap-n", type=int, default=3000)
    p.add_argument("--dev-per-family", type=int, default=2)
    p.add_argument("--skip-standard", action="store_true")
    p.add_argument("--out-root", type=Path, default=Path("outputs/rs_p0cx_trials_v1"))
    p.add_argument("--reports-root", type=Path, default=Path("reports"))
    return p.parse_args()


def _variants(raw: str) -> list[str]:
    return [x.strip() for x in str(raw).split(",") if x.strip()]


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


def _hard_files(split_dir: Path, families: set[str], *, anchor_only: bool | None) -> list[Path]:
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


def _select_dev_subset(files: list[Path], per_family: int) -> list[Path]:
    if int(per_family) <= 0:
        return list(files)
    buckets = defaultdict(list)
    for p in files:
        with np.load(p, allow_pickle=False) as z:
            buckets[str(z["scenario"])].append(p)
    out=[]
    for scenario, group in sorted(buckets.items()):
        out.extend(group[: int(per_family)])
    return sorted(out)


def _get_standard_files(root: Path, limit: int) -> list[Path]:
    files = sorted(root.glob("sample_*.npz"))
    if int(limit) > 0:
        files = files[: int(limit)]
    return files


def _maybe_cuda_synchronize(predictor: NeuralHeuristicPredictor) -> None:
    device = getattr(predictor, 'device', None)
    if device is not None and getattr(device, 'type', None) == 'cuda' and torch.cuda.is_available():
        torch.cuda.synchronize(device)


def _predict_full_standard(sample, predictor: NeuralHeuristicPredictor) -> tuple[dict[str, Any], float]:
    _maybe_cuda_synchronize(predictor)
    t0 = time.perf_counter()
    base = _euclidean_field(sample.occupancy, (sample.goal[0], sample.goal[1]), float(sample.resolution), fill_value=1e6)
    pred = predictor.predict_field(
        occupancy=sample.occupancy,
        esdf=np.zeros_like(sample.occupancy, dtype=np.float32),
        start=sample.start,
        goal=sample.goal,
        resolution=float(sample.resolution),
        base_field_override=base,
    )
    field = _resolve_2d_heuristic(pred, sample.occupancy)
    _maybe_cuda_synchronize(predictor)
    infer_ms = (time.perf_counter() - t0) * 1000.0
    res = _astar_grid(sample.occupancy, float(sample.resolution), (sample.start[0], sample.start[1]), (sample.goal[0], sample.goal[1]), 50000, heuristic_map=field, heuristic_weight=1.0)
    return res, float(infer_ms)


def _current_full_hard(case: dict[str, Any], predictor: NeuralHeuristicPredictor, cfg: CXGlobalConfig, cap: int) -> dict[str, Any]:
    anchor = _make_ours_anchor(
        case,
        predictor,
        0.675,
        cfg.residual_clip,
        cfg.residual_bias_quantile,
        cfg.residual_corridor_threshold,
        cfg.residual_corridor_suppress,
        cfg.residual_topq_quantile,
        cfg.residual_contrastive_bg_quantile,
        cfg.residual_contrastive_neg_scale,
        cfg.residual_contrastive_pos_scale,
        cfg.residual_floor_ratio,
        0,
        0.0,
        1.0,
        0.0,
        0.0,
        1.0,
        0.45,
        cfg.residual_open_boost_topq,
        cfg.residual_open_boost_min_line_clearance,
        0.0,
        0.0,
        0.95,
        False,
    )
    return _run_hybrid_method(case, anchor, max_expansions=int(cap))


def _build_hard_cache(files: list[Path], predictor: NeuralHeuristicPredictor, cfg: CXGlobalConfig, cap: int, tag: str) -> list[dict[str, Any]]:
    cache = []
    total = len(files)
    for i, p in enumerate(files, start=1):
        case = _load_nonholonomic_case(p)
        rs_field = _compute_case_rs_field(case, yaw_bins_cap=cfg.rs_field_yaw_bins)
        hybrid = _run_hybrid_method(case, _make_rs_anchor(case, rs_field=rs_field), max_expansions=cap)
        full = _current_full_hard(case, predictor, cfg, cap)
        with np.load(p, allow_pickle=False) as z:
            source = str(z.get("source_dataset", "unknown"))
        cache.append({'path': p, 'case': case, 'source': source, 'rs_field': rs_field, 'hybrid': hybrid, 'full': full})
        if i % 5 == 0 or i == total:
            print(f"[rs-p0cx:{tag}] hard cache {i}/{total}")
    return cache


def _summary_from_rows(rows: list[dict[str, Any]], n_boot: int) -> dict[str, Any]:
    succ_delta = np.asarray([r['cx_success'] - r['hybrid_success'] for r in rows], dtype=np.float64)
    exp_delta = np.asarray([r['hybrid_expansions'] - r['cx_expansions'] for r in rows], dtype=np.float64)
    time_delta = np.asarray([r['hybrid_time_ms'] - r['cx_time_ms'] for r in rows], dtype=np.float64)
    path_delta = np.asarray([r['hybrid_path_length'] - r['cx_path_length'] for r in rows if np.isfinite(r['hybrid_path_length']) and np.isfinite(r['cx_path_length'])], dtype=np.float64)
    fam = defaultdict(list)
    for r in rows:
        fam[r['scenario']].append(r)
    fam_rows = []
    for scen, vals in sorted(fam.items()):
        base_exp = float(np.mean([v['hybrid_expansions'] for v in vals]))
        cx_exp = float(np.mean([v['cx_expansions'] for v in vals]))
        base_t = float(np.mean([v['hybrid_time_ms'] for v in vals]))
        cx_t = float(np.mean([v['cx_time_ms'] for v in vals]))
        fam_rows.append({
            'scenario': scen,
            'num_cases': len(vals),
            'success_delta_pp': 100.0 * float(np.mean([v['cx_success'] - v['hybrid_success'] for v in vals])),
            'exp_delta_pct': 100.0 * (base_exp - cx_exp) / max(abs(base_exp), 1e-12),
            'time_delta_pct': 100.0 * (base_t - cx_t) / max(abs(base_t), 1e-12),
        })
    return {
        'num_pairs': len(rows),
        'success_delta': dict(zip(['mean','ci95_lo','ci95_hi','p_boot_le0'], _bootstrap_mean_ci(succ_delta, n_boot))),
        'exp_delta': dict(zip(['mean','ci95_lo','ci95_hi','p_boot_le0'], _bootstrap_mean_ci(exp_delta, n_boot))),
        'time_delta': dict(zip(['mean','ci95_lo','ci95_hi','p_boot_le0'], _bootstrap_mean_ci(time_delta, n_boot))),
        'path_delta': dict(zip(['mean','ci95_lo','ci95_hi','p_boot_le0'], _bootstrap_mean_ci(path_delta, n_boot))) if len(path_delta) else None,
        'family_rows': fam_rows,
    }


def _select_trial(trials: list[dict[str, Any]]) -> dict[str, Any]:
    ranked = []
    for tr in trials:
        s = tr['dev_summary']
        path_mean = 0.0 if s['path_delta'] is None else float(s['path_delta']['mean'])
        if path_mean < -0.05:
            continue
        ranked.append((float(s['success_delta']['mean']), float(s['exp_delta']['mean']), float(s['time_delta']['mean']), tr))
    if not ranked:
        ranked = [(float(t['dev_summary']['success_delta']['mean']), float(t['dev_summary']['exp_delta']['mean']), float(t['dev_summary']['time_delta']['mean']), t) for t in trials]
    ranked.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
    return ranked[0][3]


def _run_module_hard(key: str, predictor: NeuralHeuristicPredictor, cfg: CXGlobalConfig, dev_cache, test_cache, anchor_cache, n_boot: int):
    mod = importlib.import_module(CX_MODULES[key])
    build_nonh = getattr(mod, 'build_nonholonomic_field')
    grid_fn = getattr(mod, 'param_grid')
    trials = []
    for params in grid_fn():
        memory = mod.build_dev_memory(dev_cache, predictor, cfg, params) if key == 'CX-D' else None
        dev_rows=[]
        for item in dev_cache:
            if key == 'CX-D':
                field3d = build_nonh(item['case'], predictor, cfg, params, memory)
            else:
                field3d = build_nonh(item['case'], predictor, cfg, params)
            cx = _run_hybrid_method(item['case'], _make_rs_anchor(item['case'], rs_field=field3d), max_expansions=3500)
            dev_rows.append({
                'sample_name': item['path'].name,
                'scenario': str(item['case']['scenario']),
                'hybrid_success': float(item['hybrid']['success']),
                'hybrid_expansions': float(item['hybrid']['expansions']),
                'hybrid_path_length': float(_path_length(item['hybrid']['path'])) if item['hybrid']['path'] else float('nan'),
                'hybrid_time_ms': float(item['hybrid']['runtime_ms']),
                'full_success': float(item['full']['success']),
                'full_expansions': float(item['full']['expansions']),
                'full_time_ms': float(item['full']['runtime_ms']),
                'cx_success': float(cx['success']),
                'cx_expansions': float(cx['expansions']),
                'cx_path_length': float(_path_length(cx['path'])) if cx['path'] else float('nan'),
                'cx_time_ms': float(cx['runtime_ms']),
            })
        dev_summary = _summary_from_rows(dev_rows, n_boot)
        print(f"[rs-p0cx:{key}] dev params={params.__dict__} success_delta={dev_summary['success_delta']['mean']:.6f} exp_delta={dev_summary['exp_delta']['mean']:.6f} time_delta={dev_summary['time_delta']['mean']:.6f}")
        trials.append({'params': params.__dict__, 'dev_summary': dev_summary, 'memory': memory})
    chosen = _select_trial(trials)
    print(f"[rs-p0cx:{key}] chosen params={chosen['params']}")
    chosen_params = chosen['params']
    chosen_memory = chosen['memory']

    def _eval_cache(cache):
        rows=[]
        for item in cache:
            if key == 'CX-D':
                field3d = build_nonh(item['case'], predictor, cfg, type('P', (), chosen_params)(), chosen_memory)
            else:
                field3d = build_nonh(item['case'], predictor, cfg, type('P', (), chosen_params)())
            cx = _run_hybrid_method(item['case'], _make_rs_anchor(item['case'], rs_field=field3d), max_expansions=3500)
            rows.append({
                'sample_name': item['path'].name,
                'source': item['source'],
                'scenario': str(item['case']['scenario']),
                'hybrid_success': float(item['hybrid']['success']),
                'hybrid_expansions': float(item['hybrid']['expansions']),
                'hybrid_path_length': float(_path_length(item['hybrid']['path'])) if item['hybrid']['path'] else float('nan'),
                'hybrid_time_ms': float(item['hybrid']['runtime_ms']),
                'full_success': float(item['full']['success']),
                'full_expansions': float(item['full']['expansions']),
                'full_time_ms': float(item['full']['runtime_ms']),
                'cx_success': float(cx['success']),
                'cx_expansions': float(cx['expansions']),
                'cx_path_length': float(_path_length(cx['path'])) if cx['path'] else float('nan'),
                'cx_time_ms': float(cx['runtime_ms']),
            })
        return rows, _summary_from_rows(rows, n_boot)

    test_rows, test_summary = _eval_cache(test_cache)
    anchor_rows, anchor_summary = _eval_cache(anchor_cache)
    return trials, chosen_params, test_rows, test_summary, anchor_rows, anchor_summary


def _run_module_standard(key: str, predictor: NeuralHeuristicPredictor, chosen_params: dict[str, Any], memory: Any, benchmark_root: Path, max_mp: int, max_csm: int):
    mod = importlib.import_module(CX_MODULES[key])
    build_std = getattr(mod, 'build_standard_field')
    rows=[]
    for ds, files in [('mp', _get_standard_files(benchmark_root/'mp'/'test', max_mp)), ('csm', _get_standard_files(benchmark_root/'csm'/'test', max_csm))]:
        for p in files:
            s = load_grid_sample(p)
            a = _astar_grid(s.occupancy, float(s.resolution), (s.start[0], s.start[1]), (s.goal[0], s.goal[1]), 50000, heuristic_map=None, heuristic_weight=1.0)
            full, full_infer_ms = _predict_full_standard(s, predictor)
            _maybe_cuda_synchronize(predictor)
            t0 = time.perf_counter()
            if key == 'CX-D':
                field2d = build_std(s, predictor, type('P', (), chosen_params)(), memory)
            else:
                field2d = build_std(s, predictor, type('P', (), chosen_params)())
            _maybe_cuda_synchronize(predictor)
            cx_infer_ms = (time.perf_counter() - t0) * 1000.0
            cx = run_standard_astar(s, field2d, 50000)
            rows.append({'dataset': ds,'sample_name': p.name,'astar_success': float(a['success']),'astar_expansions': float(a['expansions']),'astar_time_ms': float(a['runtime_ms']),'full_success': float(full['success']),'full_expansions': float(full['expansions']),'full_time_ms': float(full['runtime_ms'] + full_infer_ms),'full_infer_ms': float(full_infer_ms),'cx_success': float(cx['success']),'cx_expansions': float(cx['expansions']),'cx_time_ms': float(cx['runtime_ms'] + cx_infer_ms),'cx_infer_ms': float(cx_infer_ms)})
    agg=[]
    for ds in ['mp','csm']:
        grp=[r for r in rows if r['dataset']==ds]
        if not grp:
            continue
        for name,prefix in [('A*','astar'),('Full','full'),('CX','cx')]:
            agg.append({'dataset': ds, 'method': name, 'num_cases': len(grp), 'success_rate': float(np.mean([r[f'{prefix}_success'] for r in grp])), 'avg_expansions': float(np.mean([r[f'{prefix}_expansions'] for r in grp])), 'avg_time_ms': float(np.mean([r[f'{prefix}_time_ms'] for r in grp]))})
    return rows, agg


def main() -> None:
    args = parse_args()
    predictor = NeuralHeuristicPredictor(args.ours_checkpoint, device=args.device, gaussian_sigma=2.5)
    cfg = CXGlobalConfig()
    families = _families(args.families)
    t0 = time.perf_counter()
    args.out_root.mkdir(parents=True, exist_ok=True)
    args.reports_root.mkdir(parents=True, exist_ok=True)

    dev_files = _select_dev_subset(_hard_files(args.hard_benchmark_root/'dev', families, anchor_only=None), int(args.dev_per_family))
    test_files = _hard_files(args.hard_benchmark_root/'test', families, anchor_only=None)
    anchor_files = set(_hard_files(args.hard_benchmark_root/'test', families, anchor_only=True))
    dev_cache = _build_hard_cache(dev_files, predictor, cfg, args.fixed_cap, 'dev')
    test_cache = _build_hard_cache(test_files, predictor, cfg, args.fixed_cap, 'hard_test')
    anchor_cache = [item for item in test_cache if item['path'] in anchor_files]

    results=[]
    for key in _variants(args.variants):
        out_dir = args.out_root / key.lower().replace('-', '_')
        out_dir.mkdir(parents=True, exist_ok=True)
        trials, chosen_params, test_rows, test_summary, anchor_rows, anchor_summary = _run_module_hard(key, predictor, cfg, dev_cache, test_cache, anchor_cache, args.bootstrap_n)
        chosen_memory = None
        if key == 'CX-D':
            # rebuild memory for standard evaluation from chosen params
            mod = importlib.import_module(CX_MODULES[key])
            chosen_memory = mod.build_dev_memory(dev_cache, predictor, cfg, type('P', (), chosen_params)())
        std_rows, std_summary = ([], []) if args.skip_standard else _run_module_standard(key, predictor, chosen_params, chosen_memory, args.benchmark_root, args.max_mp_cases, args.max_csm_cases)

        with (out_dir/'dev_grid.json').open('w', encoding='utf-8') as f:
            json.dump({'grid': [{'params': t['params'], 'dev_summary': t['dev_summary']} for t in trials]}, f, indent=2, ensure_ascii=False)
        with (out_dir/'chosen.json').open('w', encoding='utf-8') as f:
            json.dump({'params': chosen_params, 'test_summary': test_summary, 'anchor_summary': anchor_summary}, f, indent=2, ensure_ascii=False)
        with (out_dir/'hard_test_rows.csv').open('w', newline='', encoding='utf-8') as f:
            writer=csv.DictWriter(f, fieldnames=list(test_rows[0].keys())); writer.writeheader(); writer.writerows(test_rows)
        with (out_dir/'hard_anchor_rows.csv').open('w', newline='', encoding='utf-8') as f:
            writer=csv.DictWriter(f, fieldnames=list(anchor_rows[0].keys())); writer.writeheader(); writer.writerows(anchor_rows)
        if std_rows:
            with (out_dir/'standard_rows.csv').open('w', newline='', encoding='utf-8') as f:
                writer=csv.DictWriter(f, fieldnames=list(std_rows[0].keys())); writer.writeheader(); writer.writerows(std_rows)
            with (out_dir/'standard_summary.csv').open('w', newline='', encoding='utf-8') as f:
                writer=csv.DictWriter(f, fieldnames=list(std_summary[0].keys())); writer.writeheader(); writer.writerows(std_summary)
        report_lines = [
            f'# {key} Trial Report',
            '',
            f'- chosen params: `{chosen_params}`',
            f'- hard test success delta (CX-Hybrid): `{test_summary["success_delta"]["mean"]:.6f}`',
            f'- hard test expansion delta (Hybrid-CX): `{test_summary["exp_delta"]["mean"]:.6f}`',
            f'- hard test time delta (Hybrid-CX): `{test_summary["time_delta"]["mean"]:.6f}`',
            f'- anchor-only expansion delta (Hybrid-CX): `{anchor_summary["exp_delta"]["mean"]:.6f}`',
        ]
        if std_summary:
            report_lines.extend(['', '## Standard Summary'])
            for row in std_summary:
                report_lines.append(f"- {row['dataset']} / {row['method']}: success=`{row['success_rate']:.6f}`, expansions=`{row['avg_expansions']:.3f}`, time_ms=`{row['avg_time_ms']:.3f}`")
        (args.reports_root / f'rs_p0cx_{key.lower().replace("-","_")}_v1.md').write_text('\n'.join(report_lines), encoding='utf-8')
        results.append({'key': key, 'chosen_params': chosen_params, 'hard_test_success_delta': test_summary['success_delta']['mean'], 'hard_test_exp_delta': test_summary['exp_delta']['mean'], 'hard_test_time_delta': test_summary['time_delta']['mean'], 'anchor_exp_delta': anchor_summary['exp_delta']['mean']})
        print(f"[rs-p0cx] finished {key}")

    (args.out_root/'summary.json').write_text(json.dumps({'runtime_hours': (time.perf_counter()-t0)/3600.0, 'results': results}, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"[rs-p0cx] summary={args.out_root / 'summary.json'}")


if __name__ == '__main__':
    main()
