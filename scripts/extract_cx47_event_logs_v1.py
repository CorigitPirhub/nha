from __future__ import annotations

import argparse
import csv
import importlib
import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from network.inference import NeuralHeuristicPredictor
from rs_cx.common import CXGlobalConfig
from rs_cx8.common import load_nonholonomic_assets, load_nonholonomic_contexts
from rs_cx21.common import run_hybrid_with_policy
from rs_cx47.event_substrate import EventLogBuffer, PolicyEventAdapter, cx46_feature_fn


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Extract lightweight event logs for CX46-F/J.')
    p.add_argument('--variant', type=str, choices=['cx46f', 'cx46j'], default='cx46f')
    p.add_argument('--device', type=str, default='cuda')
    p.add_argument('--split-root', type=Path, default=Path('data/split/calib_hard_v1'))
    p.add_argument('--dataset-root', type=Path, default=Path('data/benchmark/parasol_narrow/test'))
    p.add_argument('--max-cases', type=int, default=2)
    p.add_argument('--ours-checkpoint', type=Path, default=Path('outputs/checkpoints/exp3_final_manual_v11b.pt'))
    p.add_argument('--outputs-root', type=Path, default=Path('outputs/cx47_event_logs_v1'))
    return p.parse_args()


def _read_split_rows(path: Path) -> list[dict[str, str]]:
    with path.open('r', newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def main() -> None:
    args = parse_args()
    args.outputs_root.mkdir(parents=True, exist_ok=True)

    if args.variant == 'cx46f':
        mod_name = 'rs_cx46.cx46_f_rbcc'
        chosen_json = Path('outputs/rs_p0cx46_f_rbcc_v1/chosen.json')
    else:
        mod_name = 'rs_cx46.cx46_j_rrc'
        chosen_json = Path('outputs/rs_p0cx46_j_rrc_public_v1/chosen.json')

    mod = importlib.import_module(mod_name)
    params_cls = mod.param_grid()[0].__class__
    chosen = json.loads(chosen_json.read_text(encoding='utf-8'))
    params = params_cls(**chosen['params'])

    predictor = NeuralHeuristicPredictor(args.ours_checkpoint, device=args.device, gaussian_sigma=2.5)
    cfg = CXGlobalConfig()
    train_rows = _read_split_rows(args.split_root / 'calib_train.csv')
    val_rows = _read_split_rows(args.split_root / 'calib_val.csv')
    train_files = [Path(r['path']) for r in train_rows]
    val_files = [Path(r['path']) for r in val_rows]
    target_files = sorted(args.dataset_root.glob('sample_*.npz'))[: int(max(args.max_cases, 1))]

    train_assets = load_nonholonomic_assets(train_files, predictor, cfg, 20000, tag=f'{args.variant}:event-train')
    val_contexts = load_nonholonomic_contexts(val_files, predictor, cfg, tag=f'{args.variant}:event-val')
    contexts = load_nonholonomic_contexts(target_files, predictor, cfg, tag=f'{args.variant}:event-target')
    memory = mod.fit_variant(train_assets, val_contexts, predictor, cfg, params, args.outputs_root / f'fit_{args.variant}', args.device, None)

    event_rows = []
    case_rows = []
    for asset in contexts:
        asset['case']['_cx44_sample_name'] = str(asset['path'].name)
        field = mod.build_nonholonomic_field(asset['case'], predictor, cfg, params, memory)
        bundle = asset['case'].get('_cx21_bundle', asset['bundle'])
        policy = mod.make_policy(memory, params, asset['case'], bundle, field, args.device, ablation=None)
        logger = EventLogBuffer(policy_name=args.variant, feature_fn=cx46_feature_fn)
        wrapped = PolicyEventAdapter(policy, logger)
        t0 = time.perf_counter()
        plan = run_hybrid_with_policy(asset['case'], field, 20000, successor_policy=wrapped, record_expanded=False)
        prep_ms = (time.perf_counter() - t0) * 1000.0
        rows = logger.export_rows()
        for row in rows:
            row['method'] = args.variant
            event_rows.append(row)
        stats = getattr(policy, 'stats', {}) if hasattr(policy, 'stats') else {}
        case_rows.append(
            {
                'sample_name': str(asset['path'].name),
                'scenario': str(asset['case']['scenario']),
                'method': args.variant,
                'time_ms': float(plan.runtime_ms + prep_ms),
                'success': float(plan.success),
                'expansions': float(plan.expansions),
                'witness_hits': float(stats.get('witness_hits', 0.0)),
                'witness_store_negative': float(stats.get('witness_store_negative', 0.0)),
                'witness_full_reviews': float(stats.get('witness_full_reviews', 0.0)),
                'num_events': int(len(rows)),
            }
        )

    event_path = args.outputs_root / f'{args.variant}_events.csv'
    case_path = args.outputs_root / f'{args.variant}_cases.csv'
    if event_rows:
        pd.DataFrame(event_rows).to_csv(event_path, index=False)
    pd.DataFrame(case_rows).to_csv(case_path, index=False)
    print(event_path)
    print(case_path)


if __name__ == '__main__':
    main()
