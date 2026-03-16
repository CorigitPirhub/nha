from __future__ import annotations

import argparse
import csv
import importlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from network.inference import NeuralHeuristicPredictor
from rs_cx.common import CXGlobalConfig, fuse_nonholonomic, nonholonomic_base_and_correction
from scripts.evaluate_baselines import (
    _compute_case_rs_field,
    _load_nonholonomic_case,
    _make_rs_anchor,
    _path_length,
    _run_hybrid_method,
)

CX_MODULES = {
    "CX-A": "rs_cx.cx_a_tube",
    "CX-B": "rs_cx.cx_b_bpf",
    "CX-C": "rs_cx.cx_c_dvp",
    "CX-D": "rs_cx.cx_d_pmf",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run P0-CX public parasol ablations against frozen official baselines.")
    p.add_argument("--parasol-root", type=Path, default=Path("data/benchmark/parasol_narrow/test"))
    p.add_argument("--hard-benchmark-root", type=Path, default=Path("data/benchmark/rs_root_hard_v2"))
    p.add_argument("--chosen-root", type=Path, default=Path("outputs/rs_p0cx_main_trials_v1"))
    p.add_argument("--exp3-detail", type=Path, default=Path("outputs/paper/manual_v11b_exp3_full/logs/exp_results_detail.json"))
    p.add_argument("--exp4-detail", type=Path, default=Path("outputs/paper/manual_v11b_exp4_fair/logs/exp_results_detail.json"))
    p.add_argument("--ours-checkpoint", type=Path, default=Path("outputs/checkpoints/exp3_final_manual_v11b.pt"))
    p.add_argument("--device", type=str, default="cuda")
    p.add_argument("--variants", type=str, default="CX-A,CX-B,CX-C,CX-D")
    p.add_argument("--families", type=str, default="narrow_passage,maze,deadend_labyrinth")
    p.add_argument("--dev-per-family", type=int, default=2)
    p.add_argument("--fixed-cap-exp3", type=int, default=7000)
    p.add_argument("--fixed-cap-exp4", type=int, default=20000)
    p.add_argument("--out-root", type=Path, default=Path("outputs/rs_p0cx_ablation_v1"))
    p.add_argument("--reports-root", type=Path, default=Path("reports"))
    return p.parse_args()


def _variants(raw: str) -> list[str]:
    return [x.strip() for x in str(raw).split(",") if x.strip()]


def _families(raw: str) -> set[str]:
    return {x.strip() for x in str(raw).split(",") if x.strip()}


def _hard_dev_files(root: Path, families: set[str], per_family: int) -> list[Path]:
    buckets: dict[str, list[Path]] = defaultdict(list)
    for p in sorted((root / 'dev').glob('sample_*.npz')):
        with np.load(p, allow_pickle=False) as z:
            scenario = str(z['scenario'])
        if scenario not in families:
            continue
        buckets[scenario].append(p)
    out: list[Path] = []
    for scenario, files in sorted(buckets.items()):
        out.extend(files[: int(per_family)])
    return out


def _plain_residual_field(case: dict[str, Any], predictor: NeuralHeuristicPredictor, cfg: CXGlobalConfig, residual_alpha: float) -> np.ndarray:
    rs_base, corr3d, _ = nonholonomic_base_and_correction(case, predictor, cfg, residual_alpha=float(residual_alpha))
    return fuse_nonholonomic(rs_base, corr3d, cfg.residual_floor_ratio)


def _load_parasol_cases(parasol_root: Path, cfg: CXGlobalConfig) -> list[dict[str, Any]]:
    bundles: list[dict[str, Any]] = []
    for p in sorted(parasol_root.glob('sample_*.npz')):
        case = _load_nonholonomic_case(p)
        rs_field = _compute_case_rs_field(case, yaw_bins_cap=cfg.rs_field_yaw_bins).astype(np.float32)
        case[f'_rs_field_y{int(cfg.rs_field_yaw_bins)}'] = rs_field
        bundles.append({'path': p, 'case': case, 'rs_field': rs_field})
    return bundles


def _load_frozen_rows(path: Path, budget_name: str, allowed_methods: set[str]) -> list[dict[str, Any]]:
    rows = json.loads(path.read_text(encoding='utf-8'))
    out: list[dict[str, Any]] = []
    for row in rows:
        method = str(row['method'])
        if method not in allowed_methods:
            continue
        out.append({
            'budget': budget_name,
            'sample_name': str(row['case_id']),
            'method': method,
            'success': float(row['success']),
            'expansions': float(row['expansions']),
            'path_length': float(row['path_length']) if row['path_length'] is not None else float('nan'),
            'time_ms': float(row['runtime_ms']),
        })
    return out


def _aggregate(rows: list[dict[str, Any]], budget_name: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    method_summary: list[dict[str, Any]] = []
    family_summary: list[dict[str, Any]] = []
    methods = sorted({str(r['method']) for r in rows if r['budget'] == budget_name})
    for method in methods:
        grp = [r for r in rows if r['budget'] == budget_name and r['method'] == method]
        method_summary.append({
            'budget': budget_name,
            'method': method,
            'num_cases': len(grp),
            'success_rate': float(np.mean([r['success'] for r in grp])),
            'avg_expansions': float(np.mean([r['expansions'] for r in grp])),
            'avg_path_length': float(np.nanmean([r['path_length'] for r in grp])),
            'avg_time_ms': float(np.mean([r['time_ms'] for r in grp])),
        })
    fam_methods: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        if r['budget'] == budget_name:
            fam_methods[(str(r['scenario']), str(r['method']))].append(r)
    for (scenario, method), grp in sorted(fam_methods.items()):
        family_summary.append({
            'budget': budget_name,
            'scenario': scenario,
            'method': method,
            'num_cases': len(grp),
            'success_rate': float(np.mean([r['success'] for r in grp])),
            'avg_expansions': float(np.mean([r['expansions'] for r in grp])),
            'avg_time_ms': float(np.mean([r['time_ms'] for r in grp])),
        })
    return method_summary, family_summary


def _method_lookup(summary_rows: list[dict[str, Any]], budget_name: str, method: str) -> dict[str, Any]:
    for row in summary_rows:
        if row['budget'] == budget_name and row['method'] == method:
            return row
    raise KeyError((budget_name, method))


def main() -> None:
    args = parse_args()
    predictor = NeuralHeuristicPredictor(args.ours_checkpoint, device=args.device, gaussian_sigma=2.5)
    cfg = CXGlobalConfig()
    args.out_root.mkdir(parents=True, exist_ok=True)
    args.reports_root.mkdir(parents=True, exist_ok=True)

    parasol_cases = _load_parasol_cases(args.parasol_root, cfg)
    print(f'[rs-p0cx-ablation] preload parasol cases={len(parasol_cases)}')
    scenario_map = {item['path'].name: str(item['case']['scenario']) for item in parasol_cases}

    exp3_frozen = _load_frozen_rows(args.exp3_detail, 'exp3', {'Full', 'No-Residual', 'No-RS'})
    exp4_frozen = _load_frozen_rows(args.exp4_detail, 'exp4', {'Hybrid A* (RS)', 'Ours'})
    print(f'[rs-p0cx-ablation] loaded frozen rows exp3={len(exp3_frozen)} exp4={len(exp4_frozen)}')

    dev_files = _hard_dev_files(args.hard_benchmark_root, _families(args.families), args.dev_per_family)
    dev_cache = [{'path': p, 'case': _load_nonholonomic_case(p)} for p in dev_files]

    for key in _variants(args.variants):
        chosen_path = args.chosen_root / key.lower().replace('-', '_') / 'chosen.json'
        if not chosen_path.exists():
            raise FileNotFoundError(f'missing chosen params for {key}: {chosen_path}')
        chosen = json.loads(chosen_path.read_text(encoding='utf-8'))
        params = chosen['params']
        print(f'[rs-p0cx-ablation:{key}] chosen params={params}')

        mod = importlib.import_module(CX_MODULES[key])
        build_nonh = getattr(mod, 'build_nonholonomic_field')
        memory = None
        if key == 'CX-D':
            memory = mod.build_dev_memory(dev_cache, predictor, cfg, type('P', (), params)())

        rows: list[dict[str, Any]] = []
        for row in exp3_frozen + exp4_frozen:
            rows.append({**row, 'scenario': scenario_map[row['sample_name']]})

        total = len(parasol_cases)
        for i, item in enumerate(parasol_cases, start=1):
            case = item['case']
            sample_name = item['path'].name
            plain_field = _plain_residual_field(case, predictor, cfg, params['residual_alpha'])
            cx_field = build_nonh(case, predictor, cfg, type('P', (), params)(), memory) if key == 'CX-D' else build_nonh(case, predictor, cfg, type('P', (), params)())
            for budget_name, budget in [('exp3', args.fixed_cap_exp3), ('exp4', args.fixed_cap_exp4)]:
                plain = _run_hybrid_method(case, _make_rs_anchor(case, rs_field=plain_field), max_expansions=int(budget))
                cx = _run_hybrid_method(case, _make_rs_anchor(case, rs_field=cx_field), max_expansions=int(budget))
                for method, result in [('Plain-Residual', plain), (key, cx)]:
                    rows.append({
                        'budget': budget_name,
                        'sample_name': sample_name,
                        'scenario': str(case['scenario']),
                        'method': method,
                        'success': float(result['success']),
                        'expansions': float(result['expansions']),
                        'path_length': float(_path_length(result['path'])) if result['path'] else float('nan'),
                        'time_ms': float(result['runtime_ms']),
                    })
            if i % 5 == 0 or i == total:
                print(f'[rs-p0cx-ablation:{key}] parasol {i}/{total}')

        method_summary: list[dict[str, Any]] = []
        family_summary: list[dict[str, Any]] = []
        for budget_name in ['exp3', 'exp4']:
            ms, fs = _aggregate(rows, budget_name)
            method_summary.extend(ms)
            family_summary.extend(fs)

        out_dir = args.out_root / key.lower().replace('-', '_')
        out_dir.mkdir(parents=True, exist_ok=True)
        with (out_dir / 'case_rows.csv').open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        with (out_dir / 'method_summary.csv').open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(method_summary[0].keys()))
            writer.writeheader()
            writer.writerows(method_summary)
        with (out_dir / 'family_summary.csv').open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(family_summary[0].keys()))
            writer.writeheader()
            writer.writerows(family_summary)

        report_lines = [f'# {key} Ablation Report', '', f'- chosen params: `{params}`']
        exp3_cx = _method_lookup(method_summary, 'exp3', key)
        exp3_plain = _method_lookup(method_summary, 'exp3', 'Plain-Residual')
        exp3_full = _method_lookup(method_summary, 'exp3', 'Full')
        exp3_nores = _method_lookup(method_summary, 'exp3', 'No-Residual')
        report_lines.extend([
            '',
            '## EXP3',
            f"- {key} success=`{exp3_cx['success_rate']:.6f}` vs Plain=`{exp3_plain['success_rate']:.6f}` vs Full=`{exp3_full['success_rate']:.6f}` vs No-Residual=`{exp3_nores['success_rate']:.6f}`",
            f"- {key} expansions=`{exp3_cx['avg_expansions']:.3f}` vs Plain=`{exp3_plain['avg_expansions']:.3f}` vs Full=`{exp3_full['avg_expansions']:.3f}` vs No-Residual=`{exp3_nores['avg_expansions']:.3f}`",
            f"- {key} time_ms=`{exp3_cx['avg_time_ms']:.3f}` vs Plain=`{exp3_plain['avg_time_ms']:.3f}` vs Full=`{exp3_full['avg_time_ms']:.3f}` vs No-Residual=`{exp3_nores['avg_time_ms']:.3f}`",
        ])
        exp4_cx = _method_lookup(method_summary, 'exp4', key)
        exp4_plain = _method_lookup(method_summary, 'exp4', 'Plain-Residual')
        exp4_hybrid = _method_lookup(method_summary, 'exp4', 'Hybrid A* (RS)')
        exp4_ours = _method_lookup(method_summary, 'exp4', 'Ours')
        report_lines.extend([
            '',
            '## EXP4',
            f"- {key} success=`{exp4_cx['success_rate']:.6f}` vs Plain=`{exp4_plain['success_rate']:.6f}` vs Ours=`{exp4_ours['success_rate']:.6f}` vs Hybrid=`{exp4_hybrid['success_rate']:.6f}`",
            f"- {key} expansions=`{exp4_cx['avg_expansions']:.3f}` vs Plain=`{exp4_plain['avg_expansions']:.3f}` vs Ours=`{exp4_ours['avg_expansions']:.3f}` vs Hybrid=`{exp4_hybrid['avg_expansions']:.3f}`",
            f"- {key} time_ms=`{exp4_cx['avg_time_ms']:.3f}` vs Plain=`{exp4_plain['avg_time_ms']:.3f}` vs Ours=`{exp4_ours['avg_time_ms']:.3f}` vs Hybrid=`{exp4_hybrid['avg_time_ms']:.3f}`",
        ])
        (args.reports_root / f'rs_p0cx_{key.lower().replace("-", "_")}_ablation_v1.md').write_text('\n'.join(report_lines), encoding='utf-8')
        print(f'[rs-p0cx-ablation] finished {key}')


if __name__ == '__main__':
    main()
