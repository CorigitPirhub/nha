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
    p = argparse.ArgumentParser(description='Build event-level dataset from frozen CX46 branches.')
    p.add_argument('--variants', nargs='+', default=['cx46f', 'cx46j'])
    p.add_argument('--split-root', type=Path, default=Path('data/split/calib_hard_v1'))
    p.add_argument('--ours-checkpoint', type=Path, default=Path('outputs/checkpoints/exp3_final_manual_v11b.pt'))
    p.add_argument('--device', type=str, default='cuda')
    p.add_argument('--cap', type=int, default=20000)
    p.add_argument('--outputs-root', type=Path, default=Path('outputs/cx47_event_dataset_v1'))
    return p.parse_args()


def _read_split_rows(path: Path) -> list[dict[str, str]]:
    with path.open('r', newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _load_variant(name: str):
    if name == 'cx46f':
        mod_name = 'rs_cx46.cx46_f_rbcc'
        chosen_json = Path('outputs/rs_p0cx46_f_rbcc_v1/chosen.json')
    elif name == 'cx46j':
        mod_name = 'rs_cx46.cx46_j_rrc'
        chosen_json = Path('outputs/rs_p0cx46_j_rrc_public_v1/chosen.json')
    else:
        raise ValueError(f'unsupported variant: {name}')
    mod = importlib.import_module(mod_name)
    params_cls = mod.param_grid()[0].__class__
    chosen = json.loads(chosen_json.read_text(encoding='utf-8'))
    params = params_cls(**chosen['params'])
    return mod, params


def _run_split(split_name: str, contexts, mod, params, memory, predictor, cfg, device: str, out_dir: Path, variant: str) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    event_rows: list[dict[str, object]] = []
    case_rows: list[dict[str, object]] = []
    total = len(contexts)
    for idx, asset in enumerate(contexts, start=1):
        asset['case']['_cx44_sample_name'] = str(asset['path'].name)
        field = mod.build_nonholonomic_field(asset['case'], predictor, cfg, params, memory)
        bundle = asset['case'].get('_cx21_bundle', asset['bundle'])
        policy = mod.make_policy(memory, params, asset['case'], bundle, field, device, ablation=None)
        logger = EventLogBuffer(policy_name=variant, feature_fn=cx46_feature_fn)
        wrapped = PolicyEventAdapter(policy, logger)
        t0 = time.perf_counter()
        plan = run_hybrid_with_policy(asset['case'], field, int(args.cap), successor_policy=wrapped, record_expanded=False)
        prep_ms = (time.perf_counter() - t0) * 1000.0
        stats = getattr(policy, 'stats', {}) if hasattr(policy, 'stats') else {}
        rows = logger.export_rows()
        for row in rows:
            row = dict(row)
            row['variant'] = variant
            row['split'] = split_name
            event_rows.append(row)
        case_rows.append(
            {
                'variant': variant,
                'split': split_name,
                'sample_name': str(asset['path'].name),
                'scenario': str(asset['case']['scenario']),
                'time_ms': float(plan.runtime_ms + prep_ms),
                'success': float(plan.success),
                'expansions': float(plan.expansions),
                'witness_hits': float(stats.get('witness_hits', 0.0)),
                'witness_store_negative': float(stats.get('witness_store_negative', 0.0)),
                'witness_full_reviews': float(stats.get('witness_full_reviews', 0.0)),
                'num_events': int(len(rows)),
            }
        )
        if idx % 5 == 0 or idx == total:
            print(f'[{variant}:{split_name}] {idx}/{total}', flush=True)
    return event_rows, case_rows


if __name__ == '__main__':
    args = parse_args()
    args.outputs_root.mkdir(parents=True, exist_ok=True)

    predictor = NeuralHeuristicPredictor(args.ours_checkpoint, device=args.device, gaussian_sigma=2.5)
    cfg = CXGlobalConfig()
    train_rows = _read_split_rows(args.split_root / 'calib_train.csv')
    val_rows = _read_split_rows(args.split_root / 'calib_val.csv')
    train_files = [Path(r['path']) for r in train_rows]
    val_files = [Path(r['path']) for r in val_rows]
    train_assets = load_nonholonomic_assets(train_files, predictor, cfg, int(args.cap), tag='cx47-dataset:train')
    val_contexts = load_nonholonomic_contexts(val_files, predictor, cfg, tag='cx47-dataset:val')

    all_event_rows: list[dict[str, object]] = []
    all_case_rows: list[dict[str, object]] = []
    for variant in args.variants:
        mod, params = _load_variant(variant)
        fit_dir = args.outputs_root / f'fit_{variant}'
        memory = mod.fit_variant(train_assets, val_contexts, predictor, cfg, params, fit_dir, args.device, None)
        ev_train, case_train = _run_split('train', train_assets, mod, params, memory, predictor, cfg, args.device, args.outputs_root, variant)
        ev_val, case_val = _run_split('val', val_contexts, mod, params, memory, predictor, cfg, args.device, args.outputs_root, variant)
        all_event_rows.extend(ev_train)
        all_event_rows.extend(ev_val)
        all_case_rows.extend(case_train)
        all_case_rows.extend(case_val)

    if all_event_rows:
        pd.DataFrame(all_event_rows).to_csv(args.outputs_root / 'events.csv', index=False)
    pd.DataFrame(all_case_rows).to_csv(args.outputs_root / 'cases.csv', index=False)
    print(args.outputs_root / 'events.csv')
    print(args.outputs_root / 'cases.csv')
