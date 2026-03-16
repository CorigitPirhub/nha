from __future__ import annotations

import argparse
import csv
import importlib
import json
import sys
import time
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
    p = argparse.ArgumentParser(description="Run lighter P0-CX main trials on mp/csm/parasol_narrow.")
    p.add_argument("--benchmark-root", type=Path, default=Path("data/benchmark"))
    p.add_argument("--hard-benchmark-root", type=Path, default=Path("data/benchmark/rs_root_hard_v2"))
    p.add_argument("--parasol-root", type=Path, default=Path("data/benchmark/parasol_narrow/test"))
    p.add_argument("--ours-checkpoint", type=Path, default=Path("outputs/checkpoints/exp3_final_manual_v11b.pt"))
    p.add_argument("--device", type=str, default="cuda")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--fixed-cap-exp3", type=int, default=7000)
    p.add_argument("--fixed-cap-exp4", type=int, default=20000)
    p.add_argument("--variants", type=str, default="CX-A,CX-B,CX-C,CX-D")
    p.add_argument("--dev-per-family", type=int, default=2)
    p.add_argument("--families", type=str, default="narrow_passage,maze,deadend_labyrinth")
    p.add_argument("--max-mp-cases", type=int, default=800)
    p.add_argument("--max-csm-cases", type=int, default=400)
    p.add_argument("--skip-standard", action="store_true")
    p.add_argument("--out-root", type=Path, default=Path("outputs/rs_p0cx_main_trials_v1"))
    p.add_argument("--reports-root", type=Path, default=Path("reports"))
    return p.parse_args()


def _variants(raw: str) -> list[str]:
    return [x.strip() for x in str(raw).split(",") if x.strip()]


def _families(raw: str) -> set[str]:
    return {x.strip() for x in str(raw).split(",") if x.strip()}


def _hard_dev_files(root: Path, families: set[str], per_family: int) -> list[Path]:
    buckets: dict[str, list[Path]] = {}
    for p in sorted((root / 'dev').glob('sample_*.npz')):
        with np.load(p, allow_pickle=False) as z:
            scenario = str(z['scenario'])
        if scenario not in families:
            continue
        buckets.setdefault(scenario, []).append(p)
    out: list[Path] = []
    for scenario, files in sorted(buckets.items()):
        out.extend(files[: int(per_family)])
    return out


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open('r', newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _find(rows: list[dict[str, str]], experiment: str, dataset: str, method: str) -> dict[str, str]:
    for row in rows:
        if row.get('experiment') == experiment and row.get('dataset') == dataset and row.get('method') == method:
            return row
    raise KeyError((experiment, dataset, method))


def _baseline_bundle() -> dict[str, Any]:
    exp12 = _read_csv_rows(ROOT / 'outputs/paper/manual_v11b_exp12/exp_results_summary.csv')
    exp3 = _read_csv_rows(ROOT / 'outputs/paper/manual_v11b_exp3_full/exp_results_summary.csv')
    exp4 = _read_csv_rows(ROOT / 'outputs/paper/manual_v11b_exp4_fair/exp_results_summary.csv')
    return {
        'mp_a': _find(exp12, 'exp1_mp', 'mp', 'A*'),
        'mp_full': _find(exp12, 'exp1_mp', 'mp', 'Ours'),
        'csm_a': _find(exp12, 'exp2_csm', 'csm', 'A*'),
        'csm_full': _find(exp12, 'exp2_csm', 'csm', 'Ours'),
        'exp3_full': _find(exp3, 'exp3_ablation', 'parasol', 'Full'),
        'exp3_no_res': _find(exp3, 'exp3_ablation', 'parasol', 'No-Residual'),
        'exp4_hybrid': _find(exp4, 'exp4_public_kinodynamic', 'parasol', 'Hybrid A* (RS)'),
        'exp4_full': _find(exp4, 'exp4_public_kinodynamic', 'parasol', 'Ours'),
    }


def _maybe_cuda_synchronize(predictor: NeuralHeuristicPredictor) -> None:
    device = getattr(predictor, 'device', None)
    if device is not None and getattr(device, 'type', None) == 'cuda' and torch.cuda.is_available():
        torch.cuda.synchronize(device)


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


def _build_dev_cases(dev_files: list[Path], cfg: CXGlobalConfig, cap: int) -> list[dict[str, Any]]:
    dev_cases: list[dict[str, Any]] = []
    for p in dev_files:
        case = _load_nonholonomic_case(p)
        rs_field = _compute_case_rs_field(case, yaw_bins_cap=cfg.rs_field_yaw_bins).astype(np.float32)
        case[f'_rs_field_y{int(cfg.rs_field_yaw_bins)}'] = rs_field
        hybrid = _run_hybrid_method(case, _make_rs_anchor(case, rs_field=rs_field), max_expansions=int(cap))
        dev_cases.append({'case': case, 'path': p, 'hybrid': hybrid})
    return dev_cases


def _load_parasol_cases(parasol_root: Path) -> list[dict[str, Any]]:
    return [{'path': p, 'case': _load_nonholonomic_case(p)} for p in sorted(parasol_root.glob('sample_*.npz'))]


def _select_variant_config(key: str, predictor: NeuralHeuristicPredictor, cfg: CXGlobalConfig, dev_cases: list[dict[str, Any]], cap: int):
    mod = importlib.import_module(CX_MODULES[key])
    build_nonh = getattr(mod, 'build_nonholonomic_field')
    grid = getattr(mod, 'param_grid')()
    best = None
    for params in grid:
        memory = mod.build_dev_memory(dev_cases, predictor, cfg, params) if key == 'CX-D' else None
        success: list[float] = []
        exp_delta: list[float] = []
        time_delta: list[float] = []
        path_delta: list[float] = []
        for item in dev_cases:
            if key == 'CX-D':
                field3d = build_nonh(item['case'], predictor, cfg, params, memory)
            else:
                field3d = build_nonh(item['case'], predictor, cfg, params)
            cx = _run_hybrid_method(item['case'], _make_rs_anchor(item['case'], rs_field=field3d), max_expansions=int(cap))
            success.append(float(cx['success']) - float(item['hybrid']['success']))
            exp_delta.append(float(item['hybrid']['expansions']) - float(cx['expansions']))
            time_delta.append(float(item['hybrid']['runtime_ms']) - float(cx['runtime_ms']))
            if item['hybrid']['path'] and cx['path']:
                path_delta.append(float(_path_length(item['hybrid']['path'])) - float(_path_length(cx['path'])))
        score = (float(np.mean(success)), float(np.mean(exp_delta)), float(np.mean(time_delta)))
        print(f"[rs-p0cx:{key}] dev params={params.__dict__} score={score}")
        if path_delta and float(np.mean(path_delta)) < -0.05:
            print(f"[rs-p0cx:{key}] skip params={params.__dict__} because path_delta={float(np.mean(path_delta)):.6f}")
            continue
        if best is None or score > best['score']:
            best = {'params': params.__dict__, 'memory': memory, 'score': score}
    chosen = best if best is not None else {'params': grid[0].__dict__, 'memory': None, 'score': (0.0, 0.0, 0.0)}
    print(f"[rs-p0cx:{key}] chosen params={chosen['params']} score={chosen['score']}")
    return chosen


def _eval_hard_variant(key: str, predictor: NeuralHeuristicPredictor, cfg: CXGlobalConfig, params: dict[str, Any], memory: Any, parasol_cases: list[dict[str, Any]], cap_exp3: int, cap_exp4: int) -> dict[str, Any]:
    mod = importlib.import_module(CX_MODULES[key])
    build_nonh = getattr(mod, 'build_nonholonomic_field')
    exp3_rows = []
    exp4_rows = []
    total = len(parasol_cases)
    for i, item in enumerate(parasol_cases, start=1):
        case = item['case']
        if key == 'CX-D':
            field3d = build_nonh(case, predictor, cfg, type('P', (), params)(), memory)
        else:
            field3d = build_nonh(case, predictor, cfg, type('P', (), params)())
        cx3 = _run_hybrid_method(case, _make_rs_anchor(case, rs_field=field3d), max_expansions=int(cap_exp3))
        cx4 = _run_hybrid_method(case, _make_rs_anchor(case, rs_field=field3d), max_expansions=int(cap_exp4))
        exp3_rows.append({'scenario': str(case['scenario']), 'success': float(cx3['success']), 'expansions': float(cx3['expansions']), 'path_length': float(_path_length(cx3['path'])) if cx3['path'] else float('nan'), 'time_ms': float(cx3['runtime_ms'])})
        exp4_rows.append({'scenario': str(case['scenario']), 'success': float(cx4['success']), 'expansions': float(cx4['expansions']), 'path_length': float(_path_length(cx4['path'])) if cx4['path'] else float('nan'), 'time_ms': float(cx4['runtime_ms'])})
        if i % 5 == 0 or i == total:
            print(f"[rs-p0cx:{key}] parasol {i}/{total}")

    def agg(rows: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            'num_cases': len(rows),
            'success_rate': float(np.mean([r['success'] for r in rows])),
            'avg_expansions': float(np.mean([r['expansions'] for r in rows])),
            'avg_path_length': float(np.nanmean([r['path_length'] for r in rows])),
            'avg_time_ms': float(np.mean([r['time_ms'] for r in rows])),
        }

    return {'exp3': agg(exp3_rows), 'exp4': agg(exp4_rows), 'exp3_rows': exp3_rows, 'exp4_rows': exp4_rows}


def _eval_standard_variant(key: str, predictor: NeuralHeuristicPredictor, params: dict[str, Any], memory: Any, benchmark_root: Path, max_mp: int, max_csm: int):
    mod = importlib.import_module(CX_MODULES[key])
    build_std = getattr(mod, 'build_standard_field')
    rows = []
    for ds, files in [('mp', sorted((benchmark_root / 'mp' / 'test').glob('sample_*.npz'))[:max_mp]), ('csm', sorted((benchmark_root / 'csm' / 'test').glob('sample_*.npz'))[:max_csm])]:
        for i, p in enumerate(files, start=1):
            s = load_grid_sample(p)
            _maybe_cuda_synchronize(predictor)
            t0 = time.perf_counter()
            if key == 'CX-D':
                field = build_std(s, predictor, type('P', (), params)(), memory)
            else:
                field = build_std(s, predictor, type('P', (), params)())
            _maybe_cuda_synchronize(predictor)
            infer_ms = (time.perf_counter() - t0) * 1000.0
            cx = run_standard_astar(s, field, 50000)
            rows.append({'dataset': ds, 'success': float(cx['success']), 'expansions': float(cx['expansions']), 'time_ms': float(cx['runtime_ms'] + infer_ms)})
            if i % 100 == 0 or i == len(files):
                print(f"[rs-p0cx:{key}] standard {ds} {i}/{len(files)}")
    out = {}
    for ds in ['mp', 'csm']:
        grp = [r for r in rows if r['dataset'] == ds]
        out[ds] = {
            'num_cases': len(grp),
            'success_rate': float(np.mean([r['success'] for r in grp])),
            'avg_expansions': float(np.mean([r['expansions'] for r in grp])),
            'avg_time_ms': float(np.mean([r['time_ms'] for r in grp])),
        }
    return out, rows


def main() -> None:
    args = parse_args()
    predictor = NeuralHeuristicPredictor(args.ours_checkpoint, device=args.device, gaussian_sigma=2.5)
    cfg = CXGlobalConfig()
    dev_files = _hard_dev_files(args.hard_benchmark_root, _families(args.families), args.dev_per_family)
    baseline = _baseline_bundle()
    args.out_root.mkdir(parents=True, exist_ok=True)
    args.reports_root.mkdir(parents=True, exist_ok=True)

    print(f"[rs-p0cx] preload dev cases={len(dev_files)}")
    dev_cases = _build_dev_cases(dev_files, cfg, args.fixed_cap_exp3)
    parasol_cases = _load_parasol_cases(args.parasol_root)
    print(f"[rs-p0cx] preload parasol cases={len(parasol_cases)}")

    summary = []
    t0 = time.perf_counter()
    for key in _variants(args.variants):
        chosen = _select_variant_config(key, predictor, cfg, dev_cases, args.fixed_cap_exp3)
        hard_eval = _eval_hard_variant(key, predictor, cfg, chosen['params'], chosen['memory'], parasol_cases, args.fixed_cap_exp3, args.fixed_cap_exp4)
        std_eval, std_rows = ({}, []) if args.skip_standard else _eval_standard_variant(key, predictor, chosen['params'], chosen['memory'], args.benchmark_root, args.max_mp_cases, args.max_csm_cases)
        out_dir = args.out_root / key.lower().replace('-', '_')
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / 'chosen.json').write_text(json.dumps({'params': chosen['params'], 'score': chosen['score'], 'hard_eval': hard_eval, 'standard_eval': std_eval}, indent=2, ensure_ascii=False), encoding='utf-8')
        with (out_dir / 'exp3_rows.csv').open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(hard_eval['exp3_rows'][0].keys()))
            writer.writeheader()
            writer.writerows(hard_eval['exp3_rows'])
        with (out_dir / 'exp4_rows.csv').open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(hard_eval['exp4_rows'][0].keys()))
            writer.writeheader()
            writer.writerows(hard_eval['exp4_rows'])
        if std_rows:
            with (out_dir / 'standard_rows.csv').open('w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=list(std_rows[0].keys()))
                writer.writeheader()
                writer.writerows(std_rows)
        report = [
            f'# {key} P0-CX Trial Report',
            '',
            f'- chosen params: `{chosen["params"]}`',
            '',
            '## Parasol Exp3 vs Frozen Baselines',
            f"- CX success: `{hard_eval['exp3']['success_rate']:.6f}` vs Full `{float(baseline['exp3_full']['success_rate']):.6f}` vs No-Residual `{float(baseline['exp3_no_res']['success_rate']):.6f}`",
            f"- CX expansions: `{hard_eval['exp3']['avg_expansions']:.3f}` vs Full `{float(baseline['exp3_full']['avg_expansions']):.3f}` vs No-Residual `{float(baseline['exp3_no_res']['avg_expansions']):.3f}`",
            f"- CX time: `{hard_eval['exp3']['avg_time_ms']:.3f}` vs Full `{float(baseline['exp3_full']['avg_time_ms']):.3f}` vs No-Residual `{float(baseline['exp3_no_res']['avg_time_ms']):.3f}`",
            '',
            '## Parasol Exp4 vs Frozen Baselines',
            f"- CX success: `{hard_eval['exp4']['success_rate']:.6f}` vs Hybrid `{float(baseline['exp4_hybrid']['success_rate']):.6f}` vs Full `{float(baseline['exp4_full']['success_rate']):.6f}`",
            f"- CX expansions: `{hard_eval['exp4']['avg_expansions']:.3f}` vs Hybrid `{float(baseline['exp4_hybrid']['avg_expansions']):.3f}` vs Full `{float(baseline['exp4_full']['avg_expansions']):.3f}`",
            f"- CX time: `{hard_eval['exp4']['avg_time_ms']:.3f}` vs Hybrid `{float(baseline['exp4_hybrid']['avg_time_ms']):.3f}` vs Full `{float(baseline['exp4_full']['avg_time_ms']):.3f}`",
        ]
        if std_eval:
            report.extend(['', '## Standard Support vs Frozen Baselines'])
            for ds in ['mp', 'csm']:
                base_a = baseline[f'{ds}_a']
                base_f = baseline[f'{ds}_full']
                cx = std_eval[ds]
                report.append(f"- {ds}: CX expansions=`{cx['avg_expansions']:.3f}` vs A* `{float(base_a['avg_expansions']):.3f}` vs Full `{float(base_f['avg_expansions']):.3f}`; CX time=`{cx['avg_time_ms']:.3f}` vs A* `{float(base_a['avg_time_ms']):.3f}` vs Full `{float(base_f['avg_time_ms']):.3f}`")
        (args.reports_root / f'rs_p0cx_{key.lower().replace("-", "_")}_main_v1.md').write_text('\n'.join(report), encoding='utf-8')
        summary.append({'key': key, 'params': chosen['params'], 'exp3_exp': hard_eval['exp3']['avg_expansions'], 'exp4_exp': hard_eval['exp4']['avg_expansions'], 'exp4_time': hard_eval['exp4']['avg_time_ms']})
        print(f"[rs-p0cx] finished {key}")

    (args.out_root / 'summary.json').write_text(json.dumps({'runtime_hours': (time.perf_counter() - t0) / 3600.0, 'summary': summary}, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"[rs-p0cx] summary={args.out_root / 'summary.json'}")


if __name__ == '__main__':
    main()
