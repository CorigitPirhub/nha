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
from rs_cx14.common import run_hybrid_with_policy
from rs_cx8.common import load_nonholonomic_assets, load_nonholonomic_contexts, write_inputs_sha256
from scripts import run_rs_p0cx14_round1_v1 as round1


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='CX14-B runtime compression sprint with locked public evaluation and conditional hard escalation.')
    p.add_argument('--split-root', type=Path, default=Path('data/split/calib_hard_v1'))
    p.add_argument('--parasol-root', type=Path, default=Path('data/benchmark/parasol_narrow/test'))
    p.add_argument('--hard-root', type=Path, default=Path('data/benchmark/rs_root_hard_v2/test'))
    p.add_argument('--benchmark-root', type=Path, default=Path('data/benchmark'))
    p.add_argument('--ours-checkpoint', type=Path, default=Path('outputs/checkpoints/exp3_final_manual_v11b.pt'))
    p.add_argument('--device', type=str, default='cuda')
    p.add_argument('--dev-cap', type=int, default=20000)
    p.add_argument('--exp3-cap', type=int, default=7000)
    p.add_argument('--exp4-cap', type=int, default=20000)
    p.add_argument('--hard-cap', type=int, default=20000)
    p.add_argument('--parasol-limit', type=int, default=0)
    p.add_argument('--hard-limit', type=int, default=0)
    p.add_argument('--max-mp-cases', type=int, default=800)
    p.add_argument('--max-csm-cases', type=int, default=400)
    p.add_argument('--public-baseline-cache', type=Path, default=Path('outputs/rs_p0cx14_b_pilot_v1/public_case_rows.csv'))
    p.add_argument('--hard-baseline-cache', type=Path, default=Path('outputs/rs_p0cx9_a_final_eval_v1/hard_test_case_rows.csv'))
    p.add_argument('--out-root', type=Path, default=Path('outputs/rs_p0cx14_b_runtime_sprint_v1'))
    p.add_argument('--report-path', type=Path, default=Path('reports/rs_p0cx14_b_runtime_sprint_v1.md'))
    return p.parse_args()


def _limit(files: list[Path], limit: int) -> list[Path]:
    return files[:limit] if int(limit) > 0 else files


def _read_split_csv(path: Path) -> list[Path]:
    with path.open('r', newline='', encoding='utf-8') as f:
        return [Path(r['path']) for r in csv.DictReader(f)]


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open('r', newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _path_len(plan) -> float:
    arr = np.asarray(plan.path[:, :2], dtype=np.float32)
    if arr.shape[0] < 2:
        return float('nan')
    return float(np.sum(np.linalg.norm(arr[1:] - arr[:-1], axis=1)))


def _baseline_rows(assets: list[dict[str, Any]], cap: int, dataset: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    total = len(assets)
    for idx, asset in enumerate(assets, start=1):
        baseline = asset['baseline_result']
        rs = run_hybrid_with_policy(asset['case'], asset['bundle']['rs_base'], int(cap), successor_policy=None, record_expanded=False)
        rows.extend([
            {
                'sample_name': str(asset['path'].name),
                'scenario': str(asset['case']['scenario']),
                'method': 'Hybrid A* (RS)',
                'success': float(rs.success),
                'expansions': float(rs.expansions),
                'time_ms': float(rs.runtime_ms),
                'path_length': float(_path_len(rs)),
                'dataset': dataset,
            },
            {
                'sample_name': str(asset['path'].name),
                'scenario': str(asset['case']['scenario']),
                'method': 'CX3-D',
                'success': float(baseline.success),
                'expansions': float(baseline.expansions),
                'time_ms': float(baseline.runtime_ms),
                'path_length': float(_path_len(baseline)),
                'dataset': dataset,
            },
        ])
        if idx % 10 == 0 or idx == total:
            print(f'[baseline:{dataset}] {idx}/{total}')
    return rows


def _cached_baseline_rows(path: Path, dataset: str | None = None) -> list[dict[str, Any]]:
    rows = _read_csv(path)
    out = []
    for row in rows:
        method = str(row.get('method', ''))
        if method not in {'Hybrid A* (RS)', 'CX3-D'}:
            continue
        if dataset is not None and str(row.get('dataset', '')) != str(dataset):
            continue
        item = dict(row)
        if dataset is not None:
            item['dataset'] = str(dataset)
        out.append(item)
    return out


def _case_delta(assets: list[dict[str, Any]], eval_rows: list[dict[str, Any]]) -> tuple[dict[str, float], dict[str, dict[str, float]]]:
    family = defaultdict(list)
    rows = []
    for asset, row in zip(assets, eval_rows):
        baseline = asset['baseline_result']
        base_path = _path_len(baseline)
        cx_path = float(row['path_length']) if np.isfinite(float(row['path_length'])) else float('nan')
        item = {
            'sample_name': str(asset['path'].name),
            'scenario': str(asset['case']['scenario']),
            'success_delta': float(row['success']) - float(baseline.success),
            'exp_delta': float(baseline.expansions) - float(row['expansions']),
            'time_overhead_ratio': (float(row['time_ms']) - float(baseline.runtime_ms)) / max(float(baseline.runtime_ms), 1e-6),
            'path_delta': (float(base_path) - float(cx_path)) if np.isfinite(float(base_path)) and np.isfinite(float(cx_path)) else float('nan'),
        }
        rows.append(item)
        family[str(asset['case']['scenario'])].append(item)
    summary = {
        'success_delta_pp': 100.0 * float(np.mean([r['success_delta'] for r in rows])) if rows else 0.0,
        'exp_delta': float(np.mean([r['exp_delta'] for r in rows])) if rows else 0.0,
        'time_overhead_ratio': float(np.mean([r['time_overhead_ratio'] for r in rows])) if rows else 0.0,
        'path_delta': float(np.nanmean([r['path_delta'] for r in rows])) if rows else float('nan'),
    }
    family_summary = {
        scenario: {
            'exp_delta': float(np.mean([r['exp_delta'] for r in grp])),
            'time_overhead_ratio': float(np.mean([r['time_overhead_ratio'] for r in grp])),
        }
        for scenario, grp in family.items()
    }
    return summary, family_summary


def _eval_ablation(
    mod,
    memory: dict[str, Any],
    params_obj: Any,
    predictor,
    cfg: CXGlobalConfig,
    assets: list[dict[str, Any]],
    cap: int,
    device: str,
    dataset: str,
    spec: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = []
    total = len(assets)
    for idx, asset in enumerate(assets, start=1):
        field = mod.build_nonholonomic_field(asset['case'], predictor, cfg, params_obj, memory)
        bundle = asset['case'].get('_cx14_bundle', asset['bundle'])
        prep_t0 = time.perf_counter()
        policy = mod.make_policy(memory, params_obj, asset['case'], bundle, field, device, ablation=spec)
        prep_ms = (time.perf_counter() - prep_t0) * 1000.0
        plan = run_hybrid_with_policy(asset['case'], field, int(cap), successor_policy=policy, record_expanded=False)
        rows.append({
            'sample_name': str(asset['path'].name),
            'scenario': str(asset['case']['scenario']),
            'method': f"CX14-B ({spec['name']})",
            'success': float(plan.success),
            'expansions': float(plan.expansions),
            'time_ms': float(plan.runtime_ms + prep_ms),
            'path_length': float(_path_len(plan)),
            'dataset': dataset,
        })
        if idx % 10 == 0 or idx == total:
            print(f"[CX14-B ({spec['name']})/{dataset}] {idx}/{total}")
    return rows


def _write_report(
    path: Path,
    chosen_json: dict[str, Any],
    val_family_rows: list[dict[str, Any]],
    public_delta: list[dict[str, Any]],
    public_family: list[dict[str, Any]],
    hard_delta: list[dict[str, Any]],
    hard_family: list[dict[str, Any]],
    standard_rows: list[dict[str, Any]],
) -> None:
    lines = [
        '# P0-CX14-B Runtime Sprint V1',
        '',
        '- protocol: dev-only selection on `calib_hard_v1`, then locked public `parasol_narrow` evaluation; `rs_root_hard_v2/test` is consumed only if the public gate clears',
        f"- chosen params: `{chosen_json['params']}`",
        f"- output root: `{chosen_json['out_root']}`",
        '',
        '## Calib Val vs accepted `CX3-D`',
        f"- success_delta_pp=`{float(chosen_json['val_summary']['success_delta_pp']):.3f}`",
        f"- exp_delta=`{float(chosen_json['val_summary']['exp_delta']):.3f}`",
        f"- mean_time_overhead_ratio=`{float(chosen_json['val_summary']['time_overhead_ratio']):.6f}`",
        '',
        '## Calib Family Breakdown',
    ]
    for row in val_family_rows:
        lines.append(
            f"- `{row['scenario']}`: exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['time_overhead_ratio']):.6f}`"
        )
    lines += ['', '## Public Parasol vs `CX3-D`']
    for row in public_delta:
        lines.append(
            f"- `{row['dataset']}` / `{row['method']}`: success_delta_pp=`{float(row['success_delta_pp']):.3f}`, exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`"
        )
    lines += ['', '## Public `exp4` Family Breakdown']
    for row in public_family:
        if row['dataset'] == 'exp4':
            lines.append(
                f"- `{row['scenario']}` / `{row['method']}`: success_delta_pp=`{float(row['success_delta_pp']):.3f}`, exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`"
            )
    lines += ['', '## Hard Benchmark vs `CX3-D`']
    if hard_delta:
        for row in hard_delta:
            lines.append(
                f"- `{row['method']}`: success_delta_pp=`{float(row['success_delta_pp']):.3f}`, exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`, path_delta=`{float(row['path_delta']):.3f}`"
            )
    else:
        lines.append('- skipped: public gate did not clear, so hard-test evidence was not consumed.')
    lines += ['', '## Hard Family Breakdown']
    if hard_family:
        for row in hard_family:
            if row['method'] == 'CX14-B (Full)':
                lines.append(
                    f"- `{row['scenario']}`: success_delta_pp=`{float(row['success_delta_pp']):.3f}`, exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`"
                )
    else:
        lines.append('- skipped: no hard-family rows because hard escalation was not triggered.')
    lines += ['', '## Standard Support Audit']
    for row in standard_rows:
        lines.append(
            f"- `{row['dataset']}`: num_cases=`{row['num_cases']}`, max_abs_field_diff=`{float(row['max_abs_field_diff']):.6f}`, mean_abs_field_diff=`{float(row['mean_abs_field_diff']):.6f}`"
        )
    public_full = next((r for r in public_delta if r['dataset'] == 'exp4' and r['method'] == 'CX14-B (Full)'), None)
    hard_full = next((r for r in hard_delta if r['method'] == 'CX14-B (Full)'), None)
    flange = next((r for r in public_family if r['dataset'] == 'exp4' and r['method'] == 'CX14-B (Full)' and r['scenario'] == 'flange'), None)
    lines += ['', '## Final Readout']
    if public_full is None or flange is None:
        lines.append('- result: missing evaluation rows.')
    else:
        passed_public = float(public_full['exp_delta']) > 0.0 and float(public_full['mean_time_overhead_ratio']) < 0.30 and float(flange['exp_delta']) >= 0.0
        if hard_full is None:
            if passed_public:
                lines.append('- result: public gate is cleared; hard benchmark should be consumed next under the locked config.')
            else:
                lines.append('- result: runtime compression does not clear the public gate under the locked protocol, so hard-test escalation is skipped.')
        elif passed_public:
            passed_hard = float(hard_full['exp_delta']) > 0.0 and float(hard_full['success_delta_pp']) >= 0.0
            if passed_hard:
                lines.append('- result: runtime compression clears the public gate and keeps a positive hard-benchmark trend; candidate merits accepted-promotion review.')
            else:
                lines.append('- result: public gate is cleared, but the hard benchmark does not sustain a strong enough positive trend for promotion.')
        else:
            lines.append('- result: runtime compression does not clear the public gate under the locked protocol.')
    path.write_text('\n'.join(lines), encoding='utf-8')


def main() -> None:
    args = parse_args()
    args.out_root.mkdir(parents=True, exist_ok=True)
    args.report_path.parent.mkdir(parents=True, exist_ok=True)

    mod = importlib.import_module('rs_cx14.cx14_b_lhu')
    predictor = NeuralHeuristicPredictor(args.ours_checkpoint, device=args.device, gaussian_sigma=2.5)
    cfg = CXGlobalConfig()

    train_files = _read_split_csv(args.split_root / 'calib_train.csv')
    val_files = _read_split_csv(args.split_root / 'calib_val.csv')
    public_files = _limit(sorted(args.parasol_root.glob('sample_*.npz')), int(args.parasol_limit))
    hard_files = _limit(sorted(args.hard_root.glob('sample_*.npz')), int(args.hard_limit))

    train_assets = load_nonholonomic_assets(train_files, predictor, cfg, int(args.dev_cap), tag='cx14b-sprint:calib-train')
    val_assets = load_nonholonomic_assets(val_files, predictor, cfg, int(args.dev_cap), tag='cx14b-sprint:calib-val')
    public_assets = load_nonholonomic_contexts(public_files, predictor, cfg, tag='cx14b-sprint:public')
    trials = []
    for idx, params_obj in enumerate(mod.param_grid(), start=1):
        fit_dir = args.out_root / 'trials' / f'trial_{idx:02d}'
        memory = mod.fit_variant(train_assets, val_assets, predictor, cfg, params_obj, fit_dir, args.device)
        val_rows = round1._eval_variant(mod, memory, params_obj, predictor, cfg, val_assets, int(args.dev_cap), args.device, 'CX14-B (Candidate)')
        val_summary, family_summary = _case_delta(val_assets, val_rows)
        trials.append({
            'params_obj': params_obj,
            'memory': memory,
            'val_summary': val_summary,
            'family_summary': family_summary,
        })
        print(f'[cx14b-sprint] trial={idx} params={params_obj} summary={val_summary}')

    chosen = round1._choose_trial(trials)
    chosen_params = chosen['params_obj']
    chosen_memory = chosen['memory']

    public_rows = []
    for dataset, cap in [('exp3', int(args.exp3_cap)), ('exp4', int(args.exp4_cap))]:
        assets = public_assets
        cached_public = _cached_baseline_rows(args.public_baseline_cache, dataset=dataset)
        public_rows.extend(cached_public if cached_public else _baseline_rows(assets, int(cap), dataset))
        variant_rows = round1._eval_variant(mod, chosen_memory, chosen_params, predictor, cfg, assets, int(cap), args.device, 'CX14-B (Full)')
        for row in variant_rows:
            row['dataset'] = dataset
        public_rows.extend(variant_rows)
        if dataset == 'exp4':
            for spec in mod.ablation_specs():
                public_rows.extend(_eval_ablation(mod, chosen_memory, chosen_params, predictor, cfg, assets, int(cap), args.device, dataset, spec))

    round1._write_csv(args.out_root / 'public_case_rows.csv', public_rows)
    public_summary = round1._summary(public_rows, ('dataset', 'method'))
    public_delta = round1._delta(public_summary, ('dataset',), baseline_method='CX3-D')
    public_family = round1._family_delta(public_rows, ('dataset',), baseline_method='CX3-D')
    round1._write_csv(args.out_root / 'public_summary.csv', public_summary)
    round1._write_csv(args.out_root / 'public_delta.csv', public_delta)
    round1._write_csv(args.out_root / 'public_family_delta.csv', public_family)

    public_full = next((r for r in public_delta if r['dataset'] == 'exp4' and r['method'] == 'CX14-B (Full)'), None)
    public_flange = next((r for r in public_family if r['dataset'] == 'exp4' and r['method'] == 'CX14-B (Full)' and r['scenario'] == 'flange'), None)
    should_run_hard = bool(
        public_full is not None
        and public_flange is not None
        and float(public_full['exp_delta']) > 0.0
        and float(public_full['mean_time_overhead_ratio']) < 0.30
        and float(public_flange['exp_delta']) >= 0.0
    )

    hard_delta: list[dict[str, Any]] = []
    hard_family: list[dict[str, Any]] = []
    if should_run_hard:
        hard_assets = load_nonholonomic_contexts(hard_files, predictor, cfg, tag='cx14b-sprint:hard-test')
        cached_hard = _cached_baseline_rows(args.hard_baseline_cache, dataset=None)
        hard_rows = []
        for row in cached_hard:
            row = dict(row)
            row['dataset'] = 'hard_test'
            hard_rows.append(row)
        if not hard_rows:
            hard_rows = _baseline_rows(hard_assets, int(args.hard_cap), 'hard_test')
        hard_variant_rows = round1._eval_variant(mod, chosen_memory, chosen_params, predictor, cfg, hard_assets, int(args.hard_cap), args.device, 'CX14-B (Full)')
        for row in hard_variant_rows:
            row['dataset'] = 'hard_test'
        hard_rows.extend(hard_variant_rows)
        round1._write_csv(args.out_root / 'hard_case_rows.csv', hard_rows)
        hard_summary = round1._summary(hard_rows, ('method',))
        hard_delta = round1._delta(hard_summary, tuple(), baseline_method='CX3-D')
        hard_family = round1._family_delta(hard_rows, tuple(), baseline_method='CX3-D')
        round1._write_csv(args.out_root / 'hard_summary.csv', hard_summary)
        round1._write_csv(args.out_root / 'hard_delta.csv', hard_delta)
        round1._write_csv(args.out_root / 'hard_family_delta.csv', hard_family)

    standard_rows = round1._standard_audit(mod, chosen_memory, chosen_params, predictor, args.benchmark_root, int(args.max_mp_cases), int(args.max_csm_cases))
    round1._write_csv(args.out_root / 'standard_field_audit.csv', standard_rows)

    chosen_json = {
        'variant': 'CX14-B',
        'params': chosen_params.__dict__,
        'val_summary': chosen['val_summary'],
        'out_root': str(args.out_root),
    }
    (args.out_root / 'chosen.json').write_text(json.dumps(chosen_json, indent=2, ensure_ascii=False), encoding='utf-8')
    inputs = [args.ours_checkpoint, args.split_root / 'calib_train.csv', args.split_root / 'calib_val.csv']
    inputs += train_files + val_files + public_files + hard_files
    write_inputs_sha256(inputs, args.out_root / 'inputs_sha256.json')
    (args.out_root / 'manifest.json').write_text(
        json.dumps(
            {
                'version': 'rs_p0cx14_b_runtime_sprint_v1',
                'chosen': chosen_json,
                'inputs_sha256': json.loads((args.out_root / 'inputs_sha256.json').read_text(encoding='utf-8')),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )

    val_family_rows = [
        {
            'scenario': scenario,
            'exp_delta': float(vals['exp_delta']),
            'time_overhead_ratio': float(vals['time_overhead_ratio']),
        }
        for scenario, vals in sorted(chosen['family_summary'].items())
    ]
    _write_report(args.report_path, chosen_json, val_family_rows, public_delta, public_family, hard_delta, hard_family, standard_rows)


if __name__ == '__main__':
    main()
