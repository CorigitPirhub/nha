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
from rs_cx21.common import run_hybrid_with_policy
from rs_cx24.common import build_frozen_haa_teacher
from rs_cx8.common import load_nonholonomic_assets, load_nonholonomic_contexts, write_inputs_sha256


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Analyze CX43-D release-hit slices on public/hard.')
    p.add_argument('--split-root', type=Path, default=Path('data/split/calib_hard_v1'))
    p.add_argument('--public-root', type=Path, default=Path('data/benchmark/parasol_narrow/test'))
    p.add_argument('--hard-root', type=Path, default=Path('data/benchmark/rs_root_hard_v2/test'))
    p.add_argument('--ours-checkpoint', type=Path, default=Path('outputs/checkpoints/exp3_final_manual_v11b.pt'))
    p.add_argument('--device', type=str, default='cuda')
    p.add_argument('--fixed-cap', type=int, default=20000)
    p.add_argument('--chosen-json', type=Path, default=Path('outputs/rs_p0cx43_d_pilot_v1/chosen.json'))
    p.add_argument('--parent-public-rows', type=Path, default=Path('outputs/rs_p0cx43_d_pilot_v1/public_case_rows.csv'))
    p.add_argument('--outputs-root', type=Path, default=Path('outputs/rs_p0cx43_d_release_diag_v1'))
    p.add_argument('--reports-root', type=Path, default=Path('reports'))
    return p.parse_args()


def _read_split_rows(path: Path) -> list[dict[str, Any]]:
    with path.open('r', newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open('r', newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames: list[str] = []
    seen = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _eval_dataset(label: str, assets: list[dict[str, Any]], mod, memory, params_obj, predictor, cfg, device: str, cap: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    case_rows: list[dict[str, Any]] = []
    diag_rows: list[dict[str, Any]] = []
    total = len(assets)
    for idx, asset in enumerate(assets, start=1):
        asset['case']['_cx43_sample_name'] = str(asset['path'].name)
        field = mod.build_nonholonomic_field(asset['case'], predictor, cfg, params_obj, memory)
        bundle = asset['case'].get('_cx21_bundle', asset['bundle'])
        prep_t0 = time.perf_counter()
        policy = mod.make_policy(memory, params_obj, asset['case'], bundle, field, device, ablation=None)
        prep_ms = (time.perf_counter() - prep_t0) * 1000.0
        plan = run_hybrid_with_policy(asset['case'], field, int(cap), successor_policy=policy, record_expanded=False)
        stats = dict(getattr(policy, 'stats', {}))
        release_hits = int(round(float(stats.get('rank_release_hits', 0.0))))
        release_full = int(round(float(stats.get('rank_release_full', 0.0))))
        release_singletons = int(round(float(stats.get('rank_release_singletons', 0.0))))
        pregate_reject = int(round(float(stats.get('rank_release_pregate_reject', 0.0))))
        total_rank_calls = max(release_hits + release_full + release_singletons, 1)
        case_rows.append(
            {
                'dataset': label,
                'sample_name': str(asset['path'].name),
                'scenario': str(asset['case']['scenario']),
                'success': float(plan.success),
                'expansions': float(plan.expansions),
                'time_ms': float(plan.runtime_ms + prep_ms),
                'rank_release_hits': int(release_hits),
                'rank_release_full': int(release_full),
                'rank_release_singletons': int(release_singletons),
                'rank_release_pregate_reject': int(pregate_reject),
                'release_hit_ratio': float(release_hits / total_rank_calls),
            }
        )
        diag = list(getattr(policy, 'export_diagnostics', lambda: [])())
        for row in diag:
            diag_rows.append({'dataset': label, **row})
        if idx % 5 == 0 or idx == total:
            print(f'[cx43d-diag:{label}] {idx}/{total}', flush=True)
    return case_rows, diag_rows


def _slice_rows(diag_rows: list[dict[str, Any]], radius: int = 2) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in diag_rows:
        grouped[(str(row['dataset']), str(row['sample_name']))].append(row)
    out: list[dict[str, Any]] = []
    for (_, _), rows in grouped.items():
        rows.sort(key=lambda item: int(item['step_idx']))
        hit_indices = [idx for idx, row in enumerate(rows) if str(row.get('action')) == 'release_hit']
        for hit_idx in hit_indices[:8]:
            start = max(0, hit_idx - int(radius))
            end = min(len(rows), hit_idx + int(radius) + 1)
            for idx in range(start, end):
                row = dict(rows[idx])
                row['slice_center_idx'] = int(hit_idx)
                row['offset_from_hit'] = int(idx - hit_idx)
                out.append(row)
    return out


def _summary(case_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in case_rows:
        grouped[(str(row['dataset']), str(row['scenario']))].append(row)
    out = []
    for key, rows in sorted(grouped.items()):
        out.append(
            {
                'dataset': key[0],
                'scenario': key[1],
                'num_cases': int(len(rows)),
                'mean_release_hits': float(np.mean([float(r['rank_release_hits']) for r in rows])),
                'mean_release_full': float(np.mean([float(r['rank_release_full']) for r in rows])),
                'mean_release_singletons': float(np.mean([float(r['rank_release_singletons']) for r in rows])),
                'mean_pregate_reject': float(np.mean([float(r['rank_release_pregate_reject']) for r in rows])),
                'mean_release_ratio': float(np.mean([float(r['release_hit_ratio']) for r in rows])),
                'mean_time_ms': float(np.mean([float(r['time_ms']) for r in rows])),
            }
        )
    return out


def main() -> None:
    args = parse_args()
    args.outputs_root.mkdir(parents=True, exist_ok=True)
    args.reports_root.mkdir(parents=True, exist_ok=True)

    mod = importlib.import_module('rs_cx43.cx43_d_pgsrr')
    chosen = json.loads(args.chosen_json.read_text(encoding='utf-8'))
    params_obj = mod.CX43DPGSRRParams(**chosen['params'])

    predictor = NeuralHeuristicPredictor(args.ours_checkpoint, device=args.device, gaussian_sigma=2.5)
    cfg = CXGlobalConfig()
    train_rows = _read_split_rows(args.split_root / 'calib_train.csv')
    val_rows = _read_split_rows(args.split_root / 'calib_val.csv')
    train_files = [Path(r['path']) for r in train_rows]
    val_files = [Path(r['path']) for r in val_rows]
    public_files = sorted(args.public_root.glob('sample_*.npz'))
    hard_files = sorted(args.hard_root.glob('sample_*.npz'))
    train_assets = load_nonholonomic_assets(train_files, predictor, cfg, int(args.fixed_cap), tag='cx43d-diag:train')
    val_contexts = load_nonholonomic_contexts(val_files, predictor, cfg, tag='cx43d-diag:val')
    public_contexts = load_nonholonomic_contexts(public_files, predictor, cfg, tag='cx43d-diag:public')
    hard_contexts = load_nonholonomic_contexts(hard_files, predictor, cfg, tag='cx43d-diag:hard')
    teacher = build_frozen_haa_teacher(train_assets, val_contexts, predictor, cfg, args.device, args.outputs_root / 'haa_cache')
    memory = mod.fit_variant(train_assets, val_contexts, predictor, cfg, params_obj, args.outputs_root / 'fit', args.device, {'haa_teacher': teacher})

    public_case_rows, public_diag_rows = _eval_dataset('public', public_contexts, mod, memory, params_obj, predictor, cfg, args.device, int(args.fixed_cap))
    hard_case_rows, hard_diag_rows = _eval_dataset('hard', hard_contexts, mod, memory, params_obj, predictor, cfg, args.device, int(args.fixed_cap))
    case_rows = public_case_rows + hard_case_rows
    diag_rows = public_diag_rows + hard_diag_rows
    slice_rows = _slice_rows(diag_rows, radius=2)
    summary_rows = _summary(case_rows)

    _write_csv(args.outputs_root / 'case_release_stats.csv', case_rows)
    _write_csv(args.outputs_root / 'release_diag_rows.csv', diag_rows)
    _write_csv(args.outputs_root / 'release_hit_slices.csv', slice_rows)
    _write_csv(args.outputs_root / 'summary_by_dataset_scenario.csv', summary_rows)
    write_inputs_sha256([args.ours_checkpoint, args.chosen_json, args.split_root / 'calib_train.csv', args.split_root / 'calib_val.csv'] + train_files + val_files + public_files + hard_files, args.outputs_root / 'inputs_sha256.json')

    parent_public_rows = [row for row in _read_csv(args.parent_public_rows) if str(row.get('method')) in {'CX34-A (Full)', 'CX43-D (Full)'}]
    parent_map: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in parent_public_rows:
        parent_map[str(row['sample_name'])][str(row['method'])] = row
    public_runtime_delta_rows = []
    for row in public_case_rows:
        sample = str(row['sample_name'])
        base = parent_map.get(sample, {}).get('CX34-A (Full)')
        ours = parent_map.get(sample, {}).get('CX43-D (Full)')
        if base is None or ours is None:
            continue
        public_runtime_delta_rows.append(
            {
                'sample_name': sample,
                'scenario': str(row['scenario']),
                'cx34_time_ms': float(base['time_ms']),
                'cx43d_time_ms': float(ours['time_ms']),
                'time_delta_ms': float(ours['time_ms']) - float(base['time_ms']),
                'rank_release_hits': int(row['rank_release_hits']),
                'rank_release_full': int(row['rank_release_full']),
                'rank_release_singletons': int(row['rank_release_singletons']),
                'rank_release_pregate_reject': int(row['rank_release_pregate_reject']),
            }
        )
    _write_csv(args.outputs_root / 'public_runtime_delta_vs_cx34.csv', public_runtime_delta_rows)

    total_public_hits = int(sum(int(r['rank_release_hits']) for r in public_case_rows))
    total_public_full = int(sum(int(r['rank_release_full']) for r in public_case_rows))
    total_public_singletons = int(sum(int(r['rank_release_singletons']) for r in public_case_rows))
    total_public_pregate = int(sum(int(r['rank_release_pregate_reject']) for r in public_case_rows))
    total_hard_hits = int(sum(int(r['rank_release_hits']) for r in hard_case_rows))
    total_hard_full = int(sum(int(r['rank_release_full']) for r in hard_case_rows))
    total_hard_singletons = int(sum(int(r['rank_release_singletons']) for r in hard_case_rows))
    total_hard_pregate = int(sum(int(r['rank_release_pregate_reject']) for r in hard_case_rows))

    lines = [
        '# CX43-D Release-Hit Diagnostics V1',
        '',
        f"- chosen json: `{args.chosen_json}`",
        f"- output root: `{args.outputs_root}`",
        f"- inputs sha256: `{args.outputs_root / 'inputs_sha256.json'}`",
        '',
        '## Public Aggregate',
        f'- total_release_hits=`{total_public_hits}`',
        f'- total_fallback_full=`{total_public_full}`',
        f'- total_singletons=`{total_public_singletons}`',
        f'- total_pregate_reject=`{total_public_pregate}`',
        '',
        '## Hard Aggregate',
        f'- total_release_hits=`{total_hard_hits}`',
        f'- total_fallback_full=`{total_hard_full}`',
        f'- total_singletons=`{total_hard_singletons}`',
        f'- total_pregate_reject=`{total_hard_pregate}`',
        '',
        '## Scenario Summary',
    ]
    for row in summary_rows:
        lines.append(
            f"- `{row['dataset']}` / `{row['scenario']}`: mean_release_hits=`{float(row['mean_release_hits']):.3f}`, "
            f"mean_release_full=`{float(row['mean_release_full']):.3f}`, mean_singletons=`{float(row['mean_release_singletons']):.3f}`, "
            f"mean_pregate_reject=`{float(row['mean_pregate_reject']):.3f}`, mean_release_ratio=`{float(row['mean_release_ratio']):.6f}`, "
            f"mean_time_ms=`{float(row['mean_time_ms']):.3f}`"
        )
    lines += ['', '## Public Runtime Delta vs `CX34-A`']
    for row in sorted(public_runtime_delta_rows, key=lambda item: float(item['time_delta_ms']), reverse=True):
        lines.append(
            f"- `{row['sample_name']}` / `{row['scenario']}`: time_delta_ms=`{float(row['time_delta_ms']):.3f}`, "
            f"release_hits=`{int(row['rank_release_hits'])}`, fallback_full=`{int(row['rank_release_full'])}`, "
            f"singletons=`{int(row['rank_release_singletons'])}`, pregate_reject=`{int(row['rank_release_pregate_reject'])}`"
        )
    (args.reports_root / 'rs_p0cx43_d_release_diag_v1.md').write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    main()
