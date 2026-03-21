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
from rs_cx8.common import load_nonholonomic_assets, load_nonholonomic_contexts
from rs_cx21.common import run_hybrid_with_policy


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Run P0-CX46 round10 review-credit scheduler dev screen.')
    p.add_argument('--split-root', type=Path, default=Path('data/split/calib_hard_v1'))
    p.add_argument('--ours-checkpoint', type=Path, default=Path('outputs/checkpoints/exp3_final_manual_v11b.pt'))
    p.add_argument('--device', type=str, default='cuda')
    p.add_argument('--dev-cap', type=int, default=20000)
    p.add_argument('--outputs-root', type=Path, default=Path('outputs/rs_p0cx46_j_rrc_dev_v1'))
    return p.parse_args()


def _read_split_rows(path: Path) -> list[dict[str, Any]]:
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
        rows.append(
            {
                'sample_name': str(asset['path'].name),
                'scenario': str(asset['case']['scenario']),
                'success': float(plan.success),
                'expansions': float(plan.expansions),
                'time_ms': float(plan.runtime_ms + prep_ms),
                'witness_hits': float(stats.get('witness_hits', 0.0)),
                'credit_gate_skips': float(stats.get('credit_gate_skips', 0.0)),
            }
        )
    return rows


def main() -> None:
    args = parse_args()
    args.outputs_root.mkdir(parents=True, exist_ok=True)

    mod = importlib.import_module('rs_cx46.cx46_j_rrc')
    parent_mod = importlib.import_module('rs_cx34.cx34_a_msr')

    predictor = NeuralHeuristicPredictor(args.ours_checkpoint, device=args.device, gaussian_sigma=2.5)
    cfg = CXGlobalConfig()
    train_rows = _read_split_rows(args.split_root / 'calib_train.csv')
    val_rows = _read_split_rows(args.split_root / 'calib_val.csv')
    train_files = [Path(r['path']) for r in train_rows]
    val_files = [Path(r['path']) for r in val_rows]
    train_assets = load_nonholonomic_assets(train_files, predictor, cfg, int(args.dev_cap), tag='cx46j:train')
    val_contexts = load_nonholonomic_contexts(val_files, predictor, cfg, tag='cx46j:val')

    parent_params = parent_mod.CX34AMSRParams(**json.loads(Path('outputs/rs_p0cx34_a_pilot_v1/chosen.json').read_text(encoding='utf-8'))['params'])
    parent_memory = parent_mod.fit_variant(train_assets, val_contexts, predictor, cfg, parent_params, args.outputs_root / 'parent_fit', args.device, None)
    parent_val_rows = _eval_variant(parent_mod, parent_memory, parent_params, predictor, cfg, val_contexts, int(args.dev_cap), args.device)

    summaries = []
    for idx, params_obj in enumerate(mod.param_grid(), start=1):
        fit_dir = args.outputs_root / f'trial_{idx:02d}'
        memory = mod.fit_variant(train_assets, val_contexts, predictor, cfg, params_obj, fit_dir, args.device, None)
        rows = _eval_variant(mod, memory, params_obj, predictor, cfg, val_contexts, int(args.dev_cap), args.device)
        nowt = _eval_variant(mod, memory, params_obj, predictor, cfg, val_contexts, int(args.dev_cap), args.device, ablation={'disable_witness_transfer': True})
        time_gain = float(np.mean([float(p['time_ms']) - float(r['time_ms']) for r, p in zip(rows, parent_val_rows)]))
        pair_gain = float(np.mean([float(n['time_ms']) - float(r['time_ms']) for r, n in zip(rows, nowt)]))
        summaries.append(
            {
                'trial': idx,
                'params': params_obj.__dict__,
                'time_gain_vs_cx34': time_gain,
                'time_gain_vs_nowt': pair_gain,
                'avg_hits': float(np.mean([float(r['witness_hits']) for r in rows])),
                'avg_credit_gate_skips': float(np.mean([float(r['credit_gate_skips']) for r in rows])),
            }
        )
        print(summaries[-1], flush=True)
    Path(args.outputs_root / 'dev_summary.json').write_text(json.dumps(summaries, indent=2, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    main()
