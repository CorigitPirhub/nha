from __future__ import annotations

import argparse
import csv
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
from rs_cx.common import CXGlobalConfig
from scripts.evaluate_baselines import _load_nonholonomic_case, _make_ours_anchor, _make_rs_anchor, _path_length, _run_hybrid_method


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Expanded hard benchmark check for the best P0-CX3 candidate.')
    p.add_argument('--variant', type=str, default='CX3-C')
    p.add_argument('--hard-benchmark-root', type=Path, default=Path('data/benchmark/rs_root_hard_v2'))
    p.add_argument('--chosen-root', type=Path, default=Path('outputs/rs_p0cx3_main_trials_v1'))
    p.add_argument('--ours-checkpoint', type=Path, default=Path('outputs/checkpoints/exp3_final_manual_v11b.pt'))
    p.add_argument('--device', type=str, default='cuda')
    p.add_argument('--fixed-cap-exp3', type=int, default=7000)
    p.add_argument('--fixed-cap-exp4', type=int, default=20000)
    p.add_argument('--out-root', type=Path, default=Path('outputs/rs_p0cx3_hardcheck_v1'))
    p.add_argument('--reports-root', type=Path, default=Path('reports'))
    return p.parse_args()


MODULES = {
    'CX3-A': 'rs_cx3.cx3_a_safe',
    'CX3-B': 'rs_cx3.cx3_b_psf',
    'CX3-C': 'rs_cx3.cx3_c_ccp',
    'CX3-D': 'rs_cx3.cx3_d_hpg',
}


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


def _aggregate(rows: list[dict[str, Any]], budget_name: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    method_summary=[]
    family_summary=[]
    for method in ['Hybrid A* (RS)','Full','CX3']:
        grp=[r for r in rows if r['budget']==budget_name and r['method']==method]
        method_summary.append({'budget': budget_name,'method': method,'num_cases': len(grp),'success_rate': float(np.mean([r['success'] for r in grp])),'avg_expansions': float(np.mean([r['expansions'] for r in grp])),'avg_time_ms': float(np.mean([r['time_ms'] for r in grp]))})
    fam_methods: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        if r['budget']==budget_name:
            fam_methods[(str(r['scenario']), str(r['method']))].append(r)
    for (scenario, method), grp in sorted(fam_methods.items()):
        family_summary.append({'budget': budget_name,'scenario': scenario,'method': method,'num_cases': len(grp),'success_rate': float(np.mean([r['success'] for r in grp])),'avg_expansions': float(np.mean([r['expansions'] for r in grp])),'avg_time_ms': float(np.mean([r['time_ms'] for r in grp]))})
    return method_summary, family_summary


def main() -> None:
    args=parse_args()
    chosen_path = args.chosen_root / args.variant.lower().replace('-', '_') / 'chosen.json'
    if not chosen_path.exists():
        raise FileNotFoundError(chosen_path)
    chosen = json.loads(chosen_path.read_text(encoding='utf-8'))
    params = chosen['params']
    predictor = NeuralHeuristicPredictor(args.ours_checkpoint, device=args.device, gaussian_sigma=2.5)
    cfg = CXGlobalConfig()
    mod = __import__(MODULES[args.variant], fromlist=['x'])
    build_nonh = getattr(mod, 'build_nonholonomic_field')
    p_obj = type('P', (), params)()

    args.out_root.mkdir(parents=True, exist_ok=True)
    args.reports_root.mkdir(parents=True, exist_ok=True)

    rows=[]
    files = sorted((args.hard_benchmark_root / 'test').glob('sample_*.npz'))
    total=len(files)
    for i,p in enumerate(files, start=1):
        case=_load_nonholonomic_case(p)
        with np.load(p, allow_pickle=False) as z:
            source = str(z.get('source_dataset','unknown'))
        field3d = build_nonh(case, predictor, cfg, p_obj)
        for budget_name, budget in [('exp3', args.fixed_cap_exp3), ('exp4', args.fixed_cap_exp4)]:
            rs = _run_hybrid_method(case, _make_rs_anchor(case), max_expansions=int(budget))
            full = _current_full_hard(case, predictor, cfg, int(budget))
            cx = _run_hybrid_method(case, _make_rs_anchor(case, rs_field=field3d), max_expansions=int(budget))
            for method, result in [('Hybrid A* (RS)', rs), ('Full', full), ('CX3', cx)]:
                rows.append({'budget': budget_name,'sample_name': p.name,'scenario': str(case['scenario']),'source': source,'method': method,'success': float(result['success']),'expansions': float(result['expansions']),'path_length': float(_path_length(result['path'])) if result['path'] else float('nan'),'time_ms': float(result['runtime_ms'])})
        if i % 5 == 0 or i == total:
            print(f'[rs-p0cx3-hardcheck] {i}/{total}')

    method_summary=[]; family_summary=[]
    for budget_name in ['exp3','exp4']:
        ms, fs = _aggregate(rows, budget_name)
        method_summary.extend(ms); family_summary.extend(fs)
    out_dir = args.out_root / args.variant.lower().replace('-', '_')
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir/'case_rows.csv').open('w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    with (out_dir/'method_summary.csv').open('w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=list(method_summary[0].keys())); w.writeheader(); w.writerows(method_summary)
    with (out_dir/'family_summary.csv').open('w', newline='', encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=list(family_summary[0].keys())); w.writeheader(); w.writerows(family_summary)

    lines=[f'# {args.variant} Expanded Hard Check','','- chosen params: `{params}`','- note: no re-selection on expanded benchmark; params frozen from public-bundle main trials.']
    for budget in ['exp3','exp4']:
        lines.append('')
        lines.append(f'## {budget.upper()}')
        for method in ['Hybrid A* (RS)','Full','CX3']:
            row=next(r for r in method_summary if r['budget']==budget and r['method']==method)
            lines.append(f"- {method}: success=`{row['success_rate']:.6f}`, expansions=`{row['avg_expansions']:.3f}`, time_ms=`{row['avg_time_ms']:.3f}`")
    (args.reports_root / f'rs_p0cx3_{args.variant.lower().replace("-", "_")}_hardcheck_v1.md').write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    main()
