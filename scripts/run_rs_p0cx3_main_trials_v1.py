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
from rs_cx3.common import CXGlobalConfig
from rs_cx.common import run_standard_astar
from scripts.evaluate_baselines import _load_nonholonomic_case, _make_rs_anchor, _path_length, _run_hybrid_method

CX3_MODULES = {
    'CX3-A': 'rs_cx3.cx3_a_safe',
    'CX3-B': 'rs_cx3.cx3_b_psf',
    'CX3-C': 'rs_cx3.cx3_c_ccp',
    'CX3-D': 'rs_cx3.cx3_d_hpg',
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Run P0-CX3 main trials on mp/csm/parasol_narrow.')
    p.add_argument('--benchmark-root', type=Path, default=Path('data/benchmark'))
    p.add_argument('--hard-benchmark-root', type=Path, default=Path('data/benchmark/rs_root_hard_v2'))
    p.add_argument('--parasol-root', type=Path, default=Path('data/benchmark/parasol_narrow/test'))
    p.add_argument('--ours-checkpoint', type=Path, default=Path('outputs/checkpoints/exp3_final_manual_v11b.pt'))
    p.add_argument('--device', type=str, default='cuda')
    p.add_argument('--fixed-cap-exp3', type=int, default=7000)
    p.add_argument('--fixed-cap-exp4', type=int, default=20000)
    p.add_argument('--variants', type=str, default='CX3-A,CX3-B,CX3-C,CX3-D')
    p.add_argument('--dev-per-family', type=int, default=2)
    p.add_argument('--families', type=str, default='narrow_passage,maze,deadend_labyrinth')
    p.add_argument('--max-mp-cases', type=int, default=800)
    p.add_argument('--max-csm-cases', type=int, default=400)
    p.add_argument('--skip-standard', action='store_true')
    p.add_argument('--out-root', type=Path, default=Path('outputs/rs_p0cx3_main_trials_v1'))
    p.add_argument('--reports-root', type=Path, default=Path('reports'))
    return p.parse_args()


def _variants(raw: str) -> list[str]:
    return [x.strip() for x in str(raw).split(',') if x.strip()]


def _families(raw: str) -> set[str]:
    return {x.strip() for x in str(raw).split(',') if x.strip()}


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


def _build_dev_cases(dev_files: list[Path], cap: int) -> list[dict[str, Any]]:
    cases = []
    for p in dev_files:
        case = _load_nonholonomic_case(p)
        hybrid = _run_hybrid_method(case, _make_rs_anchor(case), max_expansions=int(cap))
        cases.append({'case': case, 'path': p, 'hybrid': hybrid})
    return cases


def _load_parasol_cases(parasol_root: Path) -> list[dict[str, Any]]:
    return [{'path': p, 'case': _load_nonholonomic_case(p)} for p in sorted(parasol_root.glob('sample_*.npz'))]


def _load_standard_samples(benchmark_root: Path, max_mp: int, max_csm: int) -> dict[str, list[Any]]:
    return {
        'mp': [load_grid_sample(p) for p in sorted((benchmark_root / 'mp' / 'test').glob('sample_*.npz'))[: int(max_mp)]],
        'csm': [load_grid_sample(p) for p in sorted((benchmark_root / 'csm' / 'test').glob('sample_*.npz'))[: int(max_csm)]],
    }


def _select_variant_config(key: str, predictor: NeuralHeuristicPredictor, cfg: CXGlobalConfig, dev_cases: list[dict[str, Any]], cap: int):
    mod = importlib.import_module(CX3_MODULES[key])
    build_nonh = getattr(mod, 'build_nonholonomic_field')
    grid = getattr(mod, 'param_grid')()
    best = None
    for params in grid:
        success = []
        exp_delta = []
        time_delta = []
        path_delta = []
        for item in dev_cases:
            field3d = build_nonh(item['case'], predictor, cfg, params)
            cx = _run_hybrid_method(item['case'], _make_rs_anchor(item['case'], rs_field=field3d), max_expansions=int(cap))
            success.append(float(cx['success']) - float(item['hybrid']['success']))
            exp_delta.append(float(item['hybrid']['expansions']) - float(cx['expansions']))
            time_delta.append(float(item['hybrid']['runtime_ms']) - float(cx['runtime_ms']))
            if item['hybrid']['path'] and cx['path']:
                path_delta.append(float(_path_length(item['hybrid']['path'])) - float(_path_length(cx['path'])))
        score = (float(np.mean(success)), float(np.mean(exp_delta)), float(np.mean(time_delta)))
        print(f'[rs-p0cx3:{key}] dev params={params.__dict__} score={score}')
        if path_delta and float(np.mean(path_delta)) < -0.75:
            print(f'[rs-p0cx3:{key}] skip params={params.__dict__} because path_delta={float(np.mean(path_delta)):.6f}')
            continue
        if best is None or score > best['score']:
            best = {'params': params.__dict__, 'score': score}
    chosen = best if best is not None else {'params': grid[0].__dict__, 'score': (0.0, 0.0, 0.0)}
    print(f'[rs-p0cx3:{key}] chosen params={chosen["params"]} score={chosen["score"]}')
    return chosen


def _eval_hard_variant(key: str, predictor: NeuralHeuristicPredictor, cfg: CXGlobalConfig, params: dict[str, Any], parasol_cases: list[dict[str, Any]], cap_exp3: int, cap_exp4: int) -> dict[str, Any]:
    mod = importlib.import_module(CX3_MODULES[key])
    build_nonh = getattr(mod, 'build_nonholonomic_field')
    exp3_rows=[]; exp4_rows=[]
    p_obj = type('P', (), params)()
    total = len(parasol_cases)
    for i, item in enumerate(parasol_cases, start=1):
        case = item['case']
        field3d = build_nonh(case, predictor, cfg, p_obj)
        cx3 = _run_hybrid_method(case, _make_rs_anchor(case, rs_field=field3d), max_expansions=int(cap_exp3))
        cx4 = _run_hybrid_method(case, _make_rs_anchor(case, rs_field=field3d), max_expansions=int(cap_exp4))
        exp3_rows.append({'scenario': str(case['scenario']), 'success': float(cx3['success']), 'expansions': float(cx3['expansions']), 'path_length': float(_path_length(cx3['path'])) if cx3['path'] else float('nan'), 'time_ms': float(cx3['runtime_ms'])})
        exp4_rows.append({'scenario': str(case['scenario']), 'success': float(cx4['success']), 'expansions': float(cx4['expansions']), 'path_length': float(_path_length(cx4['path'])) if cx4['path'] else float('nan'), 'time_ms': float(cx4['runtime_ms'])})
        if i % 5 == 0 or i == total:
            print(f'[rs-p0cx3:{key}] parasol {i}/{total}')
    def agg(rows):
        return {'num_cases': len(rows), 'success_rate': float(np.mean([r['success'] for r in rows])), 'avg_expansions': float(np.mean([r['expansions'] for r in rows])), 'avg_path_length': float(np.nanmean([r['path_length'] for r in rows])), 'avg_time_ms': float(np.mean([r['time_ms'] for r in rows]))}
    return {'exp3': agg(exp3_rows), 'exp4': agg(exp4_rows), 'exp3_rows': exp3_rows, 'exp4_rows': exp4_rows}


def _eval_standard_variant(key: str, predictor: NeuralHeuristicPredictor, params: dict[str, Any], standard_samples: dict[str, list[Any]]):
    mod = importlib.import_module(CX3_MODULES[key])
    build_std = getattr(mod, 'build_standard_field')
    rows=[]
    p_obj = type('P', (), params)()
    for ds, samples in [('mp', standard_samples['mp']), ('csm', standard_samples['csm'])]:
        for i, sample in enumerate(samples, start=1):
            _maybe_cuda_synchronize(predictor)
            t0 = time.perf_counter()
            field = build_std(sample, predictor, p_obj)
            _maybe_cuda_synchronize(predictor)
            infer_ms = (time.perf_counter() - t0) * 1000.0
            cx = run_standard_astar(sample, field, 50000)
            rows.append({'dataset': ds, 'success': float(cx['success']), 'expansions': float(cx['expansions']), 'time_ms': float(cx['runtime_ms'] + infer_ms)})
            if i % 100 == 0 or i == len(samples):
                print(f'[rs-p0cx3:{key}] standard {ds} {i}/{len(samples)}')
    out={}
    for ds in ['mp','csm']:
        grp=[r for r in rows if r['dataset']==ds]
        out[ds]={'num_cases': len(grp), 'success_rate': float(np.mean([r['success'] for r in grp])), 'avg_expansions': float(np.mean([r['expansions'] for r in grp])), 'avg_time_ms': float(np.mean([r['time_ms'] for r in grp]))}
    return out, rows


def main() -> None:
    args=parse_args()
    predictor=NeuralHeuristicPredictor(args.ours_checkpoint, device=args.device, gaussian_sigma=2.5)
    cfg=CXGlobalConfig()
    baseline=_baseline_bundle()
    args.out_root.mkdir(parents=True, exist_ok=True)
    args.reports_root.mkdir(parents=True, exist_ok=True)
    dev_files=_hard_dev_files(args.hard_benchmark_root, _families(args.families), args.dev_per_family)
    print(f'[rs-p0cx3] preload dev cases={len(dev_files)}')
    dev_cases=_build_dev_cases(dev_files, args.fixed_cap_exp3)
    parasol_cases=_load_parasol_cases(args.parasol_root)
    print(f'[rs-p0cx3] preload parasol cases={len(parasol_cases)}')
    standard_samples={'mp': [], 'csm': []} if args.skip_standard else _load_standard_samples(args.benchmark_root, args.max_mp_cases, args.max_csm_cases)
    summary=[]
    t0=time.perf_counter()
    for key in _variants(args.variants):
        chosen=_select_variant_config(key, predictor, cfg, dev_cases, args.fixed_cap_exp3)
        hard_eval=_eval_hard_variant(key, predictor, cfg, chosen['params'], parasol_cases, args.fixed_cap_exp3, args.fixed_cap_exp4)
        std_eval, std_rows = ({}, []) if args.skip_standard else _eval_standard_variant(key, predictor, chosen['params'], standard_samples)
        out_dir=args.out_root / key.lower().replace('-', '_')
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir/'chosen.json').write_text(json.dumps({'params': chosen['params'], 'score': chosen['score'], 'hard_eval': hard_eval, 'standard_eval': std_eval}, indent=2, ensure_ascii=False), encoding='utf-8')
        with (out_dir/'exp3_rows.csv').open('w', newline='', encoding='utf-8') as f:
            w=csv.DictWriter(f, fieldnames=list(hard_eval['exp3_rows'][0].keys())); w.writeheader(); w.writerows(hard_eval['exp3_rows'])
        with (out_dir/'exp4_rows.csv').open('w', newline='', encoding='utf-8') as f:
            w=csv.DictWriter(f, fieldnames=list(hard_eval['exp4_rows'][0].keys())); w.writeheader(); w.writerows(hard_eval['exp4_rows'])
        if std_rows:
            with (out_dir/'standard_rows.csv').open('w', newline='', encoding='utf-8') as f:
                w=csv.DictWriter(f, fieldnames=list(std_rows[0].keys())); w.writeheader(); w.writerows(std_rows)
        report=[
            f'# {key} P0-CX3 Trial Report','',f'- chosen params: `{chosen["params"]}`','',
            '## Parasol Exp3 vs Frozen Baselines',
            f"- CX success: `{hard_eval['exp3']['success_rate']:.6f}` vs Full `{float(baseline['exp3_full']['success_rate']):.6f}` vs No-Residual `{float(baseline['exp3_no_res']['success_rate']):.6f}`",
            f"- CX expansions: `{hard_eval['exp3']['avg_expansions']:.3f}` vs Full `{float(baseline['exp3_full']['avg_expansions']):.3f}` vs No-Residual `{float(baseline['exp3_no_res']['avg_expansions']):.3f}`",
            f"- CX time: `{hard_eval['exp3']['avg_time_ms']:.3f}` vs Full `{float(baseline['exp3_full']['avg_time_ms']):.3f}` vs No-Residual `{float(baseline['exp3_no_res']['avg_time_ms']):.3f}`",
            '', '## Parasol Exp4 vs Frozen Baselines',
            f"- CX success: `{hard_eval['exp4']['success_rate']:.6f}` vs Hybrid `{float(baseline['exp4_hybrid']['success_rate']):.6f}` vs Full `{float(baseline['exp4_full']['success_rate']):.6f}`",
            f"- CX expansions: `{hard_eval['exp4']['avg_expansions']:.3f}` vs Hybrid `{float(baseline['exp4_hybrid']['avg_expansions']):.3f}` vs Full `{float(baseline['exp4_full']['avg_expansions']):.3f}`",
            f"- CX time: `{hard_eval['exp4']['avg_time_ms']:.3f}` vs Hybrid `{float(baseline['exp4_hybrid']['avg_time_ms']):.3f}` vs Full `{float(baseline['exp4_full']['avg_time_ms']):.3f}`",
        ]
        if std_eval:
            report.extend(['','## Standard Support vs Frozen Baselines'])
            for ds in ['mp','csm']:
                base_a=baseline[f'{ds}_a']; base_f=baseline[f'{ds}_full']; cx=std_eval[ds]
                report.append(f"- {ds}: CX expansions=`{cx['avg_expansions']:.3f}` vs A* `{float(base_a['avg_expansions']):.3f}` vs Full `{float(base_f['avg_expansions']):.3f}`; CX time=`{cx['avg_time_ms']:.3f}` vs A* `{float(base_a['avg_time_ms']):.3f}` vs Full `{float(base_f['avg_time_ms']):.3f}`")
        (args.reports_root / f'rs_p0cx3_{key.lower().replace("-", "_")}_main_v1.md').write_text('\n'.join(report), encoding='utf-8')
        summary.append({'key': key, 'params': chosen['params'], 'exp3_success': hard_eval['exp3']['success_rate'], 'exp3_exp': hard_eval['exp3']['avg_expansions'], 'exp4_success': hard_eval['exp4']['success_rate'], 'exp4_exp': hard_eval['exp4']['avg_expansions'], 'exp4_time': hard_eval['exp4']['avg_time_ms'], 'standard_eval': std_eval})
        print(f'[rs-p0cx3] finished {key}')
    (args.out_root/'summary.json').write_text(json.dumps({'runtime_hours': (time.perf_counter()-t0)/3600.0, 'variants': summary}, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'[rs-p0cx3] summary={args.out_root / "summary.json"}')


if __name__ == '__main__':
    main()
