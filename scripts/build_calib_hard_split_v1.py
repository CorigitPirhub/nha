from __future__ import annotations

import argparse
import csv
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
from rs_cx8.common import accepted_cx3d_nonholonomic, run_hybrid_with_policy, sha256_file, write_inputs_sha256
from scripts.evaluate_baselines import _load_nonholonomic_case, _path_length


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Build accepted-baseline-solvable hard-family calib split from rs_root_hard_v2/dev.')
    p.add_argument('--benchmark-root', type=Path, default=Path('data/benchmark/rs_root_hard_v2'))
    p.add_argument('--ours-checkpoint', type=Path, default=Path('outputs/checkpoints/exp3_final_manual_v11b.pt'))
    p.add_argument('--device', type=str, default='cuda')
    p.add_argument('--fixed-cap', type=int, default=7000)
    p.add_argument('--required-families', type=str, default='narrow_passage,flange,maze,bug_trap,parasol_misc')
    p.add_argument('--families-filter', type=str, default='')
    p.add_argument('--train-target', type=int, default=12)
    p.add_argument('--val-target', type=int, default=6)
    p.add_argument('--out-root', type=Path, default=Path('data/split/calib_hard_v1'))
    p.add_argument('--resume', action='store_true')
    return p.parse_args()


def _families(raw: str) -> list[str]:
    return [x.strip() for x in str(raw).split(',') if x.strip()]


def _read_index(path: Path) -> dict[str, dict[str, str]]:
    with path.open('r', newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    return {row['sample_name']: row for row in rows}


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                fieldnames.append(key)
                seen.add(key)
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader(); writer.writerows(rows)


def _select_split(success_rows: list[dict[str, Any]], required_families: list[str], train_target: int, val_target: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in success_rows:
        by_family[str(row['scenario'])].append(row)
    for fam in by_family:
        by_family[fam].sort(key=lambda r: (-float(r['expansions']), float(r['runtime_ms']), str(r['sample_name'])))

    train: list[dict[str, Any]] = []
    val: list[dict[str, Any]] = []
    used: set[str] = set()

    for fam in required_families:
        group = [r for r in by_family.get(fam, []) if str(r['sample_name']) not in used]
        if group:
            train.append(group[0]); used.add(str(group[0]['sample_name']))
        group = [r for r in by_family.get(fam, []) if str(r['sample_name']) not in used]
        if group and len(val) < int(val_target):
            val.append(group[0]); used.add(str(group[0]['sample_name']))

    remaining = [r for r in success_rows if str(r['sample_name']) not in used]
    remaining.sort(key=lambda r: (-float(r['expansions']), float(r['runtime_ms']), str(r['scenario']), str(r['sample_name'])))

    def _round_robin_fill(target_rows: list[dict[str, Any]], target_n: int) -> None:
        nonlocal remaining, used
        while len(target_rows) < int(target_n) and remaining:
            picked = None
            present = {str(r['scenario']) for r in target_rows}
            for row in remaining:
                if str(row['scenario']) not in present:
                    picked = row
                    break
            if picked is None:
                picked = remaining[0]
            target_rows.append(picked)
            used.add(str(picked['sample_name']))
            remaining = [r for r in remaining if str(r['sample_name']) != str(picked['sample_name'])]

    _round_robin_fill(val, int(val_target))
    _round_robin_fill(train, int(train_target))

    meta = {
        'successful_total': int(len(success_rows)),
        'selected_train': int(len(train)),
        'selected_val': int(len(val)),
        'family_success_counts': {fam: len(rows) for fam, rows in sorted(by_family.items())},
        'required_families': list(required_families),
        'covered_required_families_train': sorted({str(r['scenario']) for r in train if str(r['scenario']) in required_families}),
        'covered_required_families_val': sorted({str(r['scenario']) for r in val if str(r['scenario']) in required_families}),
        'missing_required_families': [fam for fam in required_families if fam not in by_family],
    }
    return train, val, meta


def main() -> None:
    args = parse_args()
    args.out_root.mkdir(parents=True, exist_ok=True)
    required_families = _families(args.required_families)
    predictor = NeuralHeuristicPredictor(args.ours_checkpoint, device=args.device, gaussian_sigma=2.5)
    cfg = CXGlobalConfig()
    dev_dir = args.benchmark_root / 'dev'
    dev_index = _read_index(args.benchmark_root / 'dev_index.csv')
    files = sorted(dev_dir.glob('sample_*.npz'))
    family_filter = set(_families(args.families_filter))
    if family_filter:
        files = [p for p in files if str(dev_index.get(p.name, {}).get('scenario', '')) in family_filter]

    cache_path = args.out_root / 'screen_rows.json'
    rows: list[dict[str, Any]] = []
    processed: set[str] = set()
    if args.resume and cache_path.exists():
        rows = json.loads(cache_path.read_text(encoding='utf-8'))
        processed = {str(r['sample_name']) for r in rows}
        print(f'[build-calib-hard] resume cached_rows={len(rows)}')
    t0 = time.perf_counter()
    total = len(files)
    for i, path in enumerate(files, start=1):
        if path.name in processed:
            continue
        case = _load_nonholonomic_case(path)
        _, field = accepted_cx3d_nonholonomic(case, predictor, cfg)
        plan = run_hybrid_with_policy(case, field, int(args.fixed_cap), successor_policy=None, record_expanded=False)
        meta = dev_index.get(path.name, {})
        rows.append({
            'sample_name': path.name,
            'path': str(path),
            'scenario': str(case['scenario']),
            'difficulty': str(case['difficulty']),
            'source': str(meta.get('source', 'unknown')),
            'map_id': str(meta.get('map_id', 'unknown')),
            'success': int(bool(plan.success)),
            'expansions': float(plan.expansions),
            'runtime_ms': float(plan.runtime_ms),
            'path_length': float(_path_length([(float(p[0]), float(p[1])) for p in plan.path])) if plan.path.size > 0 else float('nan'),
        })
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding='utf-8')
        if i % 5 == 0 or i == total:
            print(f'[build-calib-hard] processed {i}/{total}')

    success_rows = [r for r in rows if int(r['success']) == 1]
    train_rows, val_rows, meta = _select_split(success_rows, required_families, int(args.train_target), int(args.val_target))

    for split_name, split_rows in [('calib_train', train_rows), ('calib_val', val_rows)]:
        for row in split_rows:
            row['split'] = split_name

    _write_csv(args.out_root / 'case_rows.csv', rows)
    _write_csv(args.out_root / 'successful_rows.csv', success_rows)
    _write_csv(args.out_root / 'calib_train.csv', train_rows)
    _write_csv(args.out_root / 'calib_val.csv', val_rows)

    inputs = [args.ours_checkpoint, args.benchmark_root / 'meta.json', args.benchmark_root / 'dev_index.csv'] + files
    write_inputs_sha256(inputs, args.out_root / 'inputs_sha256.json')

    manifest = {
        'version': 'calib_hard_v1',
        'runtime_hours': float((time.perf_counter() - t0) / 3600.0),
        'benchmark_root': str(args.benchmark_root),
        'fixed_cap': int(args.fixed_cap),
        'required_families': required_families,
        'train_target': int(args.train_target),
        'val_target': int(args.val_target),
        'selection_meta': meta,
        'inputs_sha256': json.loads((args.out_root / 'inputs_sha256.json').read_text(encoding='utf-8')),
        'selected_train': [str(r['sample_name']) for r in train_rows],
        'selected_val': [str(r['sample_name']) for r in val_rows],
    }
    (args.out_root / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')

    family_hist = defaultdict(lambda: {'all': 0, 'success': 0, 'train': 0, 'val': 0})
    for row in rows:
        family_hist[str(row['scenario'])]['all'] += 1
        family_hist[str(row['scenario'])]['success'] += int(row['success'])
    for row in train_rows:
        family_hist[str(row['scenario'])]['train'] += 1
    for row in val_rows:
        family_hist[str(row['scenario'])]['val'] += 1

    lines = [
        '# Calib Hard Split V1 Audit',
        '',
        '- source benchmark: `data/benchmark/rs_root_hard_v2/dev`',
        f'- accepted baseline: `RS + refined CX3-D / RS-HPG`, cap=`{int(args.fixed_cap)}`',
        f'- total scanned dev cases: `{len(files)}`',
        f'- successful accepted-baseline cases: `{len(success_rows)}`',
        f'- selected calib_train: `{len(train_rows)}`',
        f'- selected calib_val: `{len(val_rows)}`',
        f'- required families: `{required_families}`',
        f'- missing required families in success pool: `{meta["missing_required_families"]}`',
        '',
        '## Family Audit',
    ]
    for fam, stat in sorted(family_hist.items()):
        lines.append(f"- `{fam}`: all=`{stat['all']}`, success=`{stat['success']}`, train=`{stat['train']}`, val=`{stat['val']}`")
    lines += ['', '## Selected Train']
    for row in train_rows:
        lines.append(f"- `{row['sample_name']}` / `{row['scenario']}` / source=`{row['source']}` / expansions=`{float(row['expansions']):.1f}` / time_ms=`{float(row['runtime_ms']):.1f}`")
    lines += ['', '## Selected Val']
    for row in val_rows:
        lines.append(f"- `{row['sample_name']}` / `{row['scenario']}` / source=`{row['source']}` / expansions=`{float(row['expansions']):.1f}` / time_ms=`{float(row['runtime_ms']):.1f}`")
    (args.out_root / 'audit.md').write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    main()
