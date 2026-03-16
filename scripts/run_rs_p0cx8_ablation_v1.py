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
from rs_cx8.common import FitArtifact, choose_calib_split, load_fit_model, load_nonholonomic_assets, run_hybrid_with_policy

CX8_MODULES = {
    'CX8-A': 'rs_cx8.cx8_a_app',
    'CX8-B': 'rs_cx8.cx8_b_kfm',
    'CX8-D': 'rs_cx8.cx8_d_bca',
    'CX8-C': 'rs_cx8.cx8_c_tdg',
}

ORDER = ['CX8-A', 'CX8-B', 'CX8-D', 'CX8-C']


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Run P0-CX8 ablations on calib_val only.')
    p.add_argument('--hard-benchmark-root', type=Path, default=Path('data/benchmark/rs_root_hard_v2'))
    p.add_argument('--ours-checkpoint', type=Path, default=Path('outputs/checkpoints/exp3_final_manual_v11b.pt'))
    p.add_argument('--device', type=str, default='cuda')
    p.add_argument('--seed', type=int, default=7)
    p.add_argument('--fixed-cap-exp3', type=int, default=7000)
    p.add_argument('--chosen-root', type=Path, default=Path('outputs/rs_p0cx8_main_trials_v1'))
    p.add_argument('--split-root', type=Path, default=Path())
    p.add_argument('--out-root', type=Path, default=Path('outputs/rs_p0cx8_ablation_v1'))
    p.add_argument('--reports-root', type=Path, default=Path('reports'))
    p.add_argument('--max-calib-val-cases', type=int, default=0)
    p.add_argument('--calib-val-names', type=str, default='')
    return p.parse_args()




def _maybe_named_files(root: Path, raw: str) -> list[Path] | None:
    names = [x.strip() for x in str(raw).split(',') if x.strip()]
    if not names:
        return None
    return [root / name for name in names]


def _split_csv_files(path: Path) -> list[Path]:
    if not path or not path.exists():
        return []
    with path.open('r', newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    return [Path(row['path']) for row in rows]

def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader(); writer.writerows(rows)


def _path_length_from_plan(plan) -> float:
    if plan.path.size <= 0:
        return float('nan')
    arr = np.asarray(plan.path[:, :2], dtype=np.float32)
    if arr.shape[0] < 2:
        return float('nan')
    return float(np.sum(np.linalg.norm(arr[1:] - arr[:-1], axis=1)))


def _load_variant_state(key: str, chosen_root: Path, device: str) -> dict[str, Any]:
    mod = importlib.import_module(CX8_MODULES[key])
    chosen = json.loads((chosen_root / key.lower().replace('-', '_') / 'chosen.json').read_text(encoding='utf-8'))
    params_cls = type(mod.param_grid()[0])
    params_obj = params_cls(**chosen['params'])
    fit_dir = Path(chosen['fit_dir'])
    memory = {'artifact': None, 'params': chosen['params']}
    model_path = fit_dir / 'model.pt'
    meta_path = fit_dir / 'model_meta.json'
    if model_path.exists() and meta_path.exists():
        artifact = FitArtifact(model_path=model_path, meta_path=meta_path, best_val_loss=float(chosen.get('best_val_loss', float('nan'))), input_dim=0, output_dim=0)
        model, meta = load_fit_model(artifact, str(device))
        memory.update({'artifact': artifact, 'model': model, 'meta': meta, 'best_val_loss': float(chosen.get('best_val_loss', float('nan')))})
    return {'module': mod, 'memory': memory, 'params_obj': params_obj, 'chosen': chosen}


def main() -> None:
    args = parse_args()
    predictor = NeuralHeuristicPredictor(args.ours_checkpoint, device=args.device, gaussian_sigma=2.5)
    cfg = CXGlobalConfig()
    args.out_root.mkdir(parents=True, exist_ok=True)
    args.reports_root.mkdir(parents=True, exist_ok=True)

    dev_files = sorted((args.hard_benchmark_root / 'dev').glob('sample_*.npz'))
    split = choose_calib_split(dev_files, int(args.seed))
    split_val_files = _split_csv_files(args.split_root / 'calib_val.csv') if str(args.split_root) not in {'', '.'} else []
    calib_val_files = split_val_files or _maybe_named_files(args.hard_benchmark_root / 'dev', args.calib_val_names) or split['calib_val']
    if int(args.max_calib_val_cases) > 0:
        calib_val_files = calib_val_files[: int(args.max_calib_val_cases)]
    calib_val_assets = load_nonholonomic_assets(calib_val_files, predictor, cfg, int(args.fixed_cap_exp3), tag='rs-p0cx8:ablation-calib-val')

    selected = {key: _load_variant_state(key, args.chosen_root, args.device) for key in ORDER if (args.chosen_root / key.lower().replace('-', '_') / 'chosen.json').exists()}
    if 'CX8-C' in selected:
        selected['CX8-C']['memory']['dependencies'] = {
            'APP': {'memory': selected['CX8-A']['memory'], 'params': selected['CX8-A']['params_obj']},
            'KFM': {'memory': selected['CX8-B']['memory'], 'params': selected['CX8-B']['params_obj']},
            'BCA': {'memory': selected['CX8-D']['memory'], 'params': selected['CX8-D']['params_obj']},
        }

    rows: list[dict[str, Any]] = []
    t0 = time.perf_counter()
    for key in ORDER:
        if key not in selected:
            continue
        entry = selected[key]
        mod = entry['module']
        for asset in calib_val_assets:
            case = asset['case']
            bundle = asset['bundle']
            field = asset['field']
            ablations = mod.ablation_policies(entry['memory'], entry['params_obj'], case, bundle, field, args.device)
            accepted = run_hybrid_with_policy(case, field, int(args.fixed_cap_exp3), successor_policy=None, record_expanded=False)
            for name, policy in ablations.items():
                plan = run_hybrid_with_policy(case, field, int(args.fixed_cap_exp3), successor_policy=policy, record_expanded=False)
                rows.append({
                    'variant': key,
                    'ablation': name,
                    'sample_name': asset['path'].name,
                    'scenario': str(case['scenario']),
                    'success': float(plan.success),
                    'expansions': float(plan.expansions),
                    'time_ms': float(plan.runtime_ms),
                    'path_length': _path_length_from_plan(plan),
                    'baseline_success': float(accepted.success),
                    'baseline_expansions': float(accepted.expansions),
                    'baseline_time_ms': float(accepted.runtime_ms),
                    'baseline_path_length': _path_length_from_plan(accepted),
                })
        print(f'[rs-p0cx8-ablation] finished {key}')

    _write_csv(args.out_root / 'calib_val_case_rows.csv', rows)
    summary_rows = []
    by = defaultdict(list)
    for row in rows:
        by[(row['variant'], row['ablation'])].append(row)
    for (variant, ablation), grp in sorted(by.items()):
        summary_rows.append({
            'variant': variant,
            'ablation': ablation,
            'num_cases': int(len(grp)),
            'success_rate': float(np.mean([float(r['success']) for r in grp])),
            'avg_expansions': float(np.mean([float(r['expansions']) for r in grp])),
            'avg_time_ms': float(np.mean([float(r['time_ms']) for r in grp])),
            'success_delta_pp_vs_cx3d': 100.0 * (float(np.mean([float(r['success']) for r in grp])) - float(np.mean([float(r['baseline_success']) for r in grp]))),
            'exp_delta_vs_cx3d': float(np.mean([float(r['baseline_expansions']) - float(r['expansions']) for r in grp])),
            'time_delta_ms_vs_cx3d': float(np.mean([float(r['baseline_time_ms']) - float(r['time_ms']) for r in grp])),
        })
    _write_csv(args.out_root / 'summary_rows.csv', summary_rows)

    lines = [
        '# P0-CX8 Ablation (calib_val only)',
        '',
        '- split used: `rs_root_hard_v2/dev -> calib_val` only',
        f"- calib_val cases: `{len(calib_val_assets)}`",
        '',
        '## Summary vs accepted `CX3-D`',
    ]
    for row in summary_rows:
        lines.append(f"- `{row['variant']} / {row['ablation']}`: success_delta_pp=`{row['success_delta_pp_vs_cx3d']:.3f}`, exp_delta=`{row['exp_delta_vs_cx3d']:.3f}`, time_delta_ms=`{row['time_delta_ms_vs_cx3d']:.3f}`")
    lines += ['', f"- runtime_hours=`{(time.perf_counter() - t0) / 3600.0:.4f}`"]
    (args.reports_root / 'rs_p0cx8_ablation_v1.md').write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    main()
