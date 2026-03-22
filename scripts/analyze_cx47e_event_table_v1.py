from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from network.inference import NeuralHeuristicPredictor
from rs_cx.common import CXGlobalConfig
from rs_cx8.common import load_nonholonomic_assets, load_nonholonomic_contexts
from rs_cx21.common import run_hybrid_with_policy
from rs_cx46 import cx46_f_rbcc as cx46f
from rs_cx46 import cx46_j_rrc as cx46j


SAMPLES = [
    'sample_000000.npz',
    'sample_000001.npz',
    'sample_000002.npz',
    'sample_000009.npz',
    'sample_000010.npz',
    'sample_000016.npz',
    'sample_000017.npz',
]


def main() -> None:
    out_dir = Path('outputs/cx47e_event_table_v1')
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = Path('reports/rs_p0cx47e_event_table_v1.md')

    predictor = NeuralHeuristicPredictor(Path('outputs/checkpoints/exp3_final_manual_v11b.pt'), device='cuda', gaussian_sigma=2.5)
    cfg = CXGlobalConfig()
    train_rows = list(csv.DictReader(open('data/split/calib_hard_v1/calib_train.csv')))
    val_rows = list(csv.DictReader(open('data/split/calib_hard_v1/calib_val.csv')))
    train_files = [Path(row['path']) for row in train_rows]
    val_files = [Path(row['path']) for row in val_rows]
    target_files = [Path('data/benchmark/parasol_narrow/test') / name for name in SAMPLES]

    train_assets = load_nonholonomic_assets(train_files, predictor, cfg, 20000, tag='cx47e-table:train')
    val_contexts = load_nonholonomic_contexts(val_files, predictor, cfg, tag='cx47e-table:val')
    contexts = load_nonholonomic_contexts(target_files, predictor, cfg, tag='cx47e-table:test')

    f_params = cx46f.CX46FRBCCParams(**json.loads(Path('outputs/rs_p0cx46_f_rbcc_v1/chosen.json').read_text())['params'])
    j_params = cx46j.CX46JRRCParams(**json.loads(Path('outputs/rs_p0cx46_j_rrc_public_v1/chosen.json').read_text())['params'])
    f_memory = cx46f.fit_variant(train_assets, val_contexts, predictor, cfg, f_params, out_dir / 'fit_f', 'cuda', None)
    j_memory = cx46j.fit_variant(train_assets, val_contexts, predictor, cfg, j_params, out_dir / 'fit_j', 'cuda', None)

    rows = []
    for mod_name, mod, params, memory in [
        ('CX46-F', cx46f, f_params, f_memory),
        ('CX46-J', cx46j, j_params, j_memory),
    ]:
        for asset in contexts:
            asset['case']['_cx44_sample_name'] = str(asset['path'].name)
            field = mod.build_nonholonomic_field(asset['case'], predictor, cfg, params, memory)
            bundle = asset['case'].get('_cx21_bundle', asset['bundle'])
            t0 = time.perf_counter()
            policy = mod.make_policy(memory, params, asset['case'], bundle, field, 'cuda', ablation=None)
            prep_ms = (time.perf_counter() - t0) * 1000.0
            plan = run_hybrid_with_policy(asset['case'], field, 20000, successor_policy=policy, record_expanded=False)
            stats = getattr(policy, 'stats', {}) if hasattr(policy, 'stats') else {}
            rows.append(
                {
                    'method': mod_name,
                    'sample_name': asset['path'].name,
                    'scenario': asset['case']['scenario'],
                    'time_ms': float(plan.runtime_ms + prep_ms),
                    'success': float(plan.success),
                    'expansions': float(plan.expansions),
                    'witness_hits': float(stats.get('witness_hits', 0.0)),
                    'witness_store_negative': float(stats.get('witness_store_negative', 0.0)),
                    'witness_full_reviews': float(stats.get('witness_full_reviews', 0.0)),
                    'rbcc_certainty_avg': float(stats.get('rbcc_certainty_sum', 0.0)) / max(float(stats.get('rbcc_certainty_count', 1.0)), 1.0),
                    'credit_gate_skips': float(stats.get('credit_gate_skips', 0.0)),
                }
            )

    import pandas as pd

    df = pd.DataFrame(rows)
    df.to_csv(out_dir / 'event_table.csv', index=False)
    pivot = df.pivot_table(
        index=['sample_name', 'scenario'],
        columns='method',
        values=['time_ms', 'success', 'expansions', 'witness_hits', 'witness_store_negative', 'witness_full_reviews', 'rbcc_certainty_avg', 'credit_gate_skips'],
    )
    pivot.to_csv(out_dir / 'event_table_pivot.csv')

    lines = [
        '# CX47E Event Table V1',
        '',
        '- protocol: fixed-sample diagnostic table for `CX46-F` and `CX46-J`; no new branch promoted',
        '',
        '## Per-Sample Table',
        '',
        pivot.to_string(),
    ]
    report_path.write_text('\n'.join(lines), encoding='utf-8')
    print(report_path)


if __name__ == '__main__':
    main()
