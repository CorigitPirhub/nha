from __future__ import annotations

import argparse
import csv
import importlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from network.inference import NeuralHeuristicPredictor
from rs_cx.common import CXGlobalConfig
from rs_cx8.common import load_nonholonomic_assets, load_nonholonomic_contexts
from rs_cx21.common import run_hybrid_with_policy


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Run P0-CX47 round9 future-cost-saving dev screen.')
    p.add_argument('--split-root', type=Path, default=Path('data/split/calib_hard_v1'))
    p.add_argument('--ours-checkpoint', type=Path, default=Path('outputs/checkpoints/exp3_final_manual_v11b.pt'))
    p.add_argument('--device', type=str, default='cuda')
    p.add_argument('--dev-cap', type=int, default=20000)
    p.add_argument('--outputs-root', type=Path, default=Path('outputs/rs_p0cx47_h_dev_v1'))
    return p.parse_args()


def _read_split_rows(path: Path) -> list[dict[str, str]]:
    with path.open('r', newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _eval_variant(mod, memory, params_obj, predictor, cfg, assets, cap, device, *, ablation=None):
    rows = []
    for asset in assets:
        asset['case']['_cx44_sample_name'] = str(asset['path'].name)
        field = mod.build_nonholonomic_field(asset['case'], predictor, cfg, params_obj, memory)
        bundle = asset['case'].get('_cx21_bundle', asset['bundle'])
        t0 = time.perf_counter()
        policy = mod.make_policy(memory, params_obj, asset['case'], bundle, field, device, ablation=ablation)
        prep_ms = (time.perf_counter() - t0) * 1000.0
        plan = run_hybrid_with_policy(asset['case'], field, int(cap), successor_policy=policy, record_expanded=False)
        stats = getattr(policy, 'stats', {}) if hasattr(policy, 'stats') else {}
        value_count = max(float(stats.get('future_proxy_value_count', 0.0)), 1.0)
        period_count = max(float(stats.get('future_proxy_period_count', 0.0)), 1.0)
        rows.append(
            {
                'sample_name': str(asset['path'].name),
                'scenario': str(asset['case']['scenario']),
                'success': float(plan.success),
                'expansions': float(plan.expansions),
                'time_ms': float(plan.runtime_ms + prep_ms),
                'witness_hits': float(stats.get('witness_hits', 0.0)),
                'future_proxy_skips': float(stats.get('future_proxy_skips', 0.0)),
                'future_saved_reviews_credit': float(stats.get('future_saved_reviews_credit', 0.0)),
                'avg_future_proxy_value': float(stats.get('future_proxy_value_sum', 0.0)) / value_count,
                'avg_review_period': float(stats.get('future_proxy_period_sum', 0.0)) / period_count,
            }
        )
    return rows


def main() -> None:
    args = parse_args()
    args.outputs_root.mkdir(parents=True, exist_ok=True)

    mod = importlib.import_module('rs_cx47.cx47_h_fcs')
    cx34_mod = importlib.import_module('rs_cx34.cx34_a_msr')

    predictor = NeuralHeuristicPredictor(args.ours_checkpoint, device=args.device, gaussian_sigma=2.5)
    cfg = CXGlobalConfig()
    train_rows = _read_split_rows(args.split_root / 'calib_train.csv')
    val_rows = _read_split_rows(args.split_root / 'calib_val.csv')
    train_files = [Path(r['path']) for r in train_rows]
    val_files = [Path(r['path']) for r in val_rows]
    train_assets = load_nonholonomic_assets(train_files, predictor, cfg, int(args.dev_cap), tag='cx47h:train')
    val_contexts = load_nonholonomic_contexts(val_files, predictor, cfg, tag='cx47h:val')

    shared_parent_params = mod._to_parent_params(mod.param_grid()[0])
    shared_parent_memory = mod.parent_mod.fit_variant(train_assets, val_contexts, predictor, cfg, shared_parent_params, args.outputs_root / 'shared_parent_fit', args.device, None)

    cx34_params = cx34_mod.CX34AMSRParams(**json.loads(Path('outputs/rs_p0cx34_a_pilot_v1/chosen.json').read_text(encoding='utf-8'))['params'])
    cx34_memory = cx34_mod.fit_variant(train_assets, val_contexts, predictor, cfg, cx34_params, args.outputs_root / 'cx34_fit', args.device, None)
    cx34_rows = _eval_variant(cx34_mod, cx34_memory, cx34_params, predictor, cfg, val_contexts, int(args.dev_cap), args.device)

    future_rows, support_counter = mod._collect_rows(train_assets, predictor, cfg, shared_parent_params, shared_parent_memory, mod.param_grid()[0], args.device)
    (args.outputs_root / 'train_row_summary.json').write_text(
        json.dumps(
            {
                'num_rows': int(len(future_rows)),
                'positive_count': int(sum(1 for row in future_rows if float(row['label']) > 1e-6)),
                'zero_count': int(sum(1 for row in future_rows if float(row['label']) <= 1e-6)),
                'event_key_count': int(len({tuple(row['event_key']) for row in future_rows})),
                'avg_future_hits': float(np.mean([float(row.get('future_hits', 0.0)) for row in future_rows])) if future_rows else 0.0,
                'avg_scaled_label': float(np.mean([float(row.get('label', 0.0)) for row in future_rows])) if future_rows else 0.0,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )

    summaries = []
    for idx, params_obj in enumerate(mod.param_grid(), start=1):
        fit_dir = args.outputs_root / f'trial_{idx:02d}'
        memory = mod.fit_variant(
            train_assets,
            val_contexts,
            predictor,
            cfg,
            params_obj,
            fit_dir,
            args.device,
            dependencies={'parent_memory': shared_parent_memory, 'future_rows': future_rows, 'support_counter': support_counter},
        )
        rows = _eval_variant(mod, memory, params_obj, predictor, cfg, val_contexts, int(args.dev_cap), args.device)
        nowt = _eval_variant(mod, memory, params_obj, predictor, cfg, val_contexts, int(args.dev_cap), args.device, ablation={'disable_witness_transfer': True})
        nofp = _eval_variant(mod, memory, params_obj, predictor, cfg, val_contexts, int(args.dev_cap), args.device, ablation={'disable_future_proxy': True})
        norc = _eval_variant(mod, memory, params_obj, predictor, cfg, val_contexts, int(args.dev_cap), args.device, ablation={'disable_realized_credit': True})
        time_gain = float(np.mean([float(base['time_ms']) - float(row['time_ms']) for row, base in zip(rows, cx34_rows)]))
        pair_nowt = float(np.mean([float(base['time_ms']) - float(row['time_ms']) for row, base in zip(rows, nowt)]))
        pair_nofp = float(np.mean([float(base['time_ms']) - float(row['time_ms']) for row, base in zip(rows, nofp)]))
        pair_norc = float(np.mean([float(base['time_ms']) - float(row['time_ms']) for row, base in zip(rows, norc)]))
        summaries.append(
            {
                'trial': idx,
                'params': params_obj.__dict__,
                'time_gain_vs_cx34': time_gain,
                'time_gain_vs_nowt': pair_nowt,
                'time_gain_vs_nofp': pair_nofp,
                'time_gain_vs_norc': pair_norc,
                'avg_hits': float(np.mean([float(r['witness_hits']) for r in rows])),
                'avg_future_proxy_skips': float(np.mean([float(r['future_proxy_skips']) for r in rows])),
                'avg_future_saved_reviews_credit': float(np.mean([float(r['future_saved_reviews_credit']) for r in rows])),
                'avg_future_proxy_value': float(np.mean([float(r['avg_future_proxy_value']) for r in rows])),
                'avg_review_period': float(np.mean([float(r['avg_review_period']) for r in rows])),
            }
        )
        print(summaries[-1], flush=True)
    (args.outputs_root / 'dev_summary.json').write_text(json.dumps(summaries, indent=2, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    main()
