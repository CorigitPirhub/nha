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

from baselines.common import load_grid_sample
from network.inference import NeuralHeuristicPredictor
from rs_cx.common import CXGlobalConfig
from rs_cx10 import cx10_d_las
from rs_cx10.common import load_teacher_memory
from rs_cx12.common import (
    BASE_CHOSEN_JSON,
    compare_plan_to_baseline,
    load_base_params,
    run_hybrid_with_policy,
    scene_context,
    standard_identity_error,
)
from rs_cx8.common import load_nonholonomic_assets, load_nonholonomic_contexts, write_inputs_sha256

MODULES = {
    'CX12-A': 'rs_cx12.cx12_a_ghf',
    'CX12-C': 'rs_cx12.cx12_c_ssg',
    'CX12-B': 'rs_cx12.cx12_b_csa',
}
SLUG = {'CX12-A': 'a', 'CX12-C': 'c', 'CX12-B': 'b'}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Run P0-CX12 round1 pilots.')
    p.add_argument('--variants', type=str, default='CX12-A,CX12-C,CX12-B')
    p.add_argument('--split-root', type=Path, default=Path('data/split/calib_hard_v1'))
    p.add_argument('--guard-dev-root', type=Path, default=Path('data/benchmark/rs_root_hard_v2/dev'))
    p.add_argument('--parasol-root', type=Path, default=Path('data/benchmark/parasol_narrow/test'))
    p.add_argument('--benchmark-root', type=Path, default=Path('data/benchmark'))
    p.add_argument('--ours-checkpoint', type=Path, default=Path('outputs/checkpoints/exp3_final_manual_v11b.pt'))
    p.add_argument('--teacher-chosen-json', type=Path, default=Path('outputs/rs_p0cx8_d_hard_pilot_v1/chosen.json'))
    p.add_argument('--base-chosen-json', type=Path, default=BASE_CHOSEN_JSON)
    p.add_argument('--base-out-root', type=Path, default=Path('outputs/rs_p0cx10_d_pilot_v1'))
    p.add_argument('--device', type=str, default='cuda')
    p.add_argument('--dev-cap', type=int, default=20000)
    p.add_argument('--exp3-cap', type=int, default=7000)
    p.add_argument('--exp4-cap', type=int, default=20000)
    p.add_argument('--max-mp-cases', type=int, default=800)
    p.add_argument('--max-csm-cases', type=int, default=400)
    p.add_argument('--reports-root', type=Path, default=Path('reports'))
    p.add_argument('--outputs-root', type=Path, default=Path('outputs'))
    return p.parse_args()


def _variants(raw: str) -> list[str]:
    return [item.strip() for item in str(raw).split(',') if item.strip()]


def _read_split_csv(path: Path) -> list[Path]:
    with path.open('r', newline='', encoding='utf-8') as f:
        return [Path(r['path']) for r in csv.DictReader(f)]


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open('r', newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames = []
    seen = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def _summary(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    by = defaultdict(list)
    for row in rows:
        by[tuple(row[k] for k in keys)].append(row)
    out = []
    for key, grp in sorted(by.items()):
        item = {k: key[i] for i, k in enumerate(keys)}
        item.update({
            'num_cases': int(len(grp)),
            'success_rate': float(np.mean([float(r['success']) for r in grp])),
            'avg_expansions': float(np.mean([float(r['expansions']) for r in grp])),
            'avg_time_ms': float(np.mean([float(r['time_ms']) for r in grp])),
            'avg_path_length': float(np.nanmean([float(r['path_length']) for r in grp])) if grp else float('nan'),
        })
        out.append(item)
    return out


def _delta(summary_rows: list[dict[str, Any]], group_keys: tuple[str, ...], baseline_method: str = 'CX3-D') -> list[dict[str, Any]]:
    grouped = defaultdict(dict)
    for row in summary_rows:
        grp = tuple(row[k] for k in group_keys)
        grouped[grp][str(row['method'])] = row
    out = []
    for grp, methods in sorted(grouped.items()):
        base = methods.get(baseline_method)
        if base is None:
            continue
        for method, row in methods.items():
            if method == baseline_method:
                continue
            item = {k: grp[i] for i, k in enumerate(group_keys)}
            item.update({
                'method': method,
                'baseline': baseline_method,
                'success_delta_pp': 100.0 * (float(row['success_rate']) - float(base['success_rate'])),
                'exp_delta': float(base['avg_expansions']) - float(row['avg_expansions']),
                'time_delta_ms': float(base['avg_time_ms']) - float(row['avg_time_ms']),
                'mean_time_overhead_ratio': (float(row['avg_time_ms']) - float(base['avg_time_ms'])) / max(float(base['avg_time_ms']), 1e-6),
                'path_delta': (float(base['avg_path_length']) - float(row['avg_path_length'])) if np.isfinite(float(base['avg_path_length'])) and np.isfinite(float(row['avg_path_length'])) else float('nan'),
            })
            out.append(item)
    return out


def _family_delta(rows: list[dict[str, Any]], extra_keys: tuple[str, ...], baseline_method: str = 'CX3-D') -> list[dict[str, Any]]:
    summary = _summary(rows, extra_keys + ('scenario', 'method'))
    return _delta(summary, extra_keys + ('scenario',), baseline_method=baseline_method)


def _choose_trial(trials: list[dict[str, Any]]) -> dict[str, Any]:
    def _flange(trial):
        return float(trial['family_summary'].get('flange', {}).get('exp_delta', 0.0))
    ranked = sorted(
        trials,
        key=lambda t: (
            1 if _flange(t) >= 0.0 else 0,
            float(t['val_summary']['success_delta_pp']),
            float(t['val_summary']['exp_delta']),
            -float(t['val_summary']['time_overhead_ratio']),
        ),
        reverse=True,
    )
    feasible = [t for t in ranked if float(t['val_summary']['time_overhead_ratio']) < 0.30]
    return feasible[0] if feasible else ranked[0]


def _guard_train_files(split_root: Path, guard_dev_root: Path) -> list[Path]:
    calib_train = set(_read_split_csv(split_root / 'calib_train.csv'))
    calib_val = set(_read_split_csv(split_root / 'calib_val.csv'))
    extra = {p for p in sorted(guard_dev_root.glob('sample_*.npz')) if p not in calib_val}
    return sorted(calib_train | extra)


def _build_guard_assets(train_assets: list[dict[str, Any]], guard_assets: list[dict[str, Any]], base_memory: dict[str, Any], base_params: cx10_d_las.CX10DLASParams, cap: int, device: str) -> list[dict[str, Any]]:
    rows = []
    total = len(guard_assets)
    for idx, asset in enumerate(guard_assets, start=1):
        ctx = scene_context(base_memory, base_params, asset['case'], asset['bundle'], asset['field'], device)
        plan = run_hybrid_with_policy(asset['case'], asset['field'], int(cap), successor_policy=ctx['base_policy'], record_expanded=False) if ctx['base_policy'] is not None else asset['baseline_result']
        delta = compare_plan_to_baseline(asset['baseline_result'], plan, prep_ms=0.0)
        rows.append({
            'sample_name': str(asset['path'].name),
            'scenario': str(asset['case']['scenario']),
            'scene_context': ctx,
            **delta,
        })
        if idx % 5 == 0 or idx == total:
            print(f'[cx12:guard-cache] {idx}/{total}')
    return rows


def _eval_variant(mod, memory: dict[str, Any], params_obj: Any, predictor, cfg: CXGlobalConfig, assets: list[dict[str, Any]], cap: int, device: str, method_name: str) -> list[dict[str, Any]]:
    rows = []
    total = len(assets)
    for idx, asset in enumerate(assets, start=1):
        field = mod.build_nonholonomic_field(asset['case'], predictor, cfg, params_obj, memory)
        prep_t0 = time.perf_counter()
        policy = mod.make_policy(memory, params_obj, asset['case'], asset['bundle'], field, device, ablation=None)
        prep_ms = (time.perf_counter() - prep_t0) * 1000.0
        plan = run_hybrid_with_policy(asset['case'], field, int(cap), successor_policy=policy, record_expanded=False)
        rows.append({
            'sample_name': str(asset['path'].name),
            'scenario': str(asset['case']['scenario']),
            'method': method_name,
            'success': float(plan.success),
            'expansions': float(plan.expansions),
            'time_ms': float(plan.runtime_ms + prep_ms),
            'path_length': float(_path_len(plan)),
        })
        if idx % 5 == 0 or idx == total:
            print(f'[{method_name}] {idx}/{total}')
    return rows


def _path_len(plan) -> float:
    arr = np.asarray(plan.path[:, :2], dtype=np.float32)
    if arr.shape[0] < 2:
        return float('nan')
    return float(np.sum(np.linalg.norm(arr[1:] - arr[:-1], axis=1)))


def _standard_audit(mod, memory: dict[str, Any], params_obj: Any, predictor, benchmark_root: Path, max_mp_cases: int, max_csm_cases: int) -> list[dict[str, Any]]:
    rows = []
    for dataset, limit in [('mp', int(max_mp_cases)), ('csm', int(max_csm_cases))]:
        files = sorted((benchmark_root / dataset / 'test').glob('sample_*.npz'))[:limit]
        diffs = []
        for idx, path in enumerate(files, start=1):
            sample = load_grid_sample(path)
            diffs.append(standard_identity_error(sample, predictor, lambda s, p: mod.build_standard_field(s, p, params_obj, memory)))
            if idx % 100 == 0 or idx == len(files):
                print(f'[cx12:standard:{dataset}] {idx}/{len(files)}')
        rows.append({
            'dataset': dataset,
            'num_cases': int(len(files)),
            'max_abs_field_diff': float(max(diffs) if diffs else 0.0),
            'mean_abs_field_diff': float(np.mean(diffs) if diffs else 0.0),
        })
    return rows


def _write_report(path: Path, title: str, chosen_json: dict[str, Any], val_family: list[dict[str, Any]], public_delta: list[dict[str, Any]], public_family: list[dict[str, Any]], standard_rows: list[dict[str, Any]], readout: str) -> None:
    lines = [
        f'# {title}',
        '',
        '- protocol: base sketch locked from `outputs/rs_p0cx10_d_pilot_v1/chosen.json`; CX12 layer trained/selected only on dev data',
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
    for row in val_family:
        lines.append(f"- `{row['scenario']}`: success_delta_pp=`{float(row['success_delta_pp']):.3f}`, exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['time_overhead_ratio']):.6f}`")
    lines += ['', '## Public Parasol vs `CX3-D`']
    for row in public_delta:
        lines.append(f"- `{row['dataset']}` / `{row['method']}`: success_delta_pp=`{float(row['success_delta_pp']):.3f}`, exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`")
    lines += ['', '## `exp4` Family Breakdown']
    for row in public_family:
        if row['dataset'] == 'exp4' and row['method'] != 'Hybrid A* (RS)':
            lines.append(f"- `{row['scenario']}` / `{row['method']}`: success_delta_pp=`{float(row['success_delta_pp']):.3f}`, exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`")
    lines += ['', '## Standard Support Audit']
    for row in standard_rows:
        lines.append(f"- `{row['dataset']}`: num_cases=`{row['num_cases']}`, max_abs_field_diff=`{float(row['max_abs_field_diff']):.6f}`, mean_abs_field_diff=`{float(row['mean_abs_field_diff']):.6f}`")
    lines += ['', '## Final Readout', f'- {readout}']
    path.write_text('\n'.join(lines), encoding='utf-8')


def main() -> None:
    args = parse_args()
    args.reports_root.mkdir(parents=True, exist_ok=True)
    args.outputs_root.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()

    variants = _variants(args.variants)
    predictor = NeuralHeuristicPredictor(args.ours_checkpoint, device=args.device, gaussian_sigma=2.5)
    cfg = CXGlobalConfig()

    train_files = _read_split_csv(args.split_root / 'calib_train.csv')
    val_files = _read_split_csv(args.split_root / 'calib_val.csv')
    guard_files = _guard_train_files(args.split_root, args.guard_dev_root)
    public_files = sorted(args.parasol_root.glob('sample_*.npz'))

    train_assets = load_nonholonomic_assets(train_files, predictor, cfg, int(args.dev_cap), tag='cx12:calib-train')
    val_assets = load_nonholonomic_assets(val_files, predictor, cfg, int(args.dev_cap), tag='cx12:calib-val')
    guard_assets = load_nonholonomic_assets(guard_files, predictor, cfg, int(args.dev_cap), tag='cx12:guard-train')
    public_assets_exp3 = load_nonholonomic_contexts(public_files, predictor, cfg, tag='cx12:public-exp3')
    public_assets_exp4 = load_nonholonomic_contexts(public_files, predictor, cfg, tag='cx12:public-exp4')

    teacher_memory = load_teacher_memory(Path(args.teacher_chosen_json), args.device)
    teacher_memory['device'] = str(args.device)
    base_params = load_base_params(Path(args.base_chosen_json))
    base_memory = cx10_d_las.fit_variant(
        train_assets,
        val_assets,
        predictor,
        cfg,
        base_params,
        args.outputs_root / 'rs_p0cx12_base_refit',
        args.device,
        dependencies={'teacher_memory': teacher_memory, 'teacher_chosen_json': Path(args.teacher_chosen_json)},
    )
    guard_cache = _build_guard_assets(train_assets, guard_assets, base_memory, base_params, int(args.dev_cap), args.device)

    base_public_rows = _read_csv(args.base_out_root / 'public_case_rows.csv')
    base_public_by_dataset = defaultdict(list)
    for row in base_public_rows:
        if str(row['method']) in {'Hybrid A* (RS)', 'CX3-D', 'CX10-D (Full)'}:
            base_public_by_dataset[str(row['dataset'])].append(row)

    summary_rows = []
    for variant in variants:
        mod = importlib.import_module(MODULES[variant])
        slug = SLUG[variant]
        out_root = args.outputs_root / f'rs_p0cx12_{slug}_pilot_v1'
        out_root.mkdir(parents=True, exist_ok=True)
        report_path = args.reports_root / f'rs_p0cx12_{slug}_pilot_v1.md'
        deps = {
            'base_memory': base_memory,
            'base_params': base_params,
            'guard_assets': guard_assets,
            'guard_cache': guard_cache,
            'dev_cap': int(args.dev_cap),
        }
        trials = []
        for idx, params_obj in enumerate(mod.param_grid(), start=1):
            fit_dir = out_root / 'trials' / f'trial_{idx:02d}'
            memory = mod.fit_variant(guard_assets, val_assets, predictor, cfg, params_obj, fit_dir, args.device, dependencies=deps)
            val_rows = _eval_variant(mod, memory, params_obj, predictor, cfg, val_assets, int(args.dev_cap), args.device, f'{variant} (Candidate)')
            val_case_rows = []
            family = defaultdict(list)
            for asset, row in zip(val_assets, val_rows):
                baseline = asset['baseline_result']
                base_path = _path_len(baseline)
                cx_path = float(row['path_length']) if np.isfinite(float(row['path_length'])) else float('nan')
                case_row = {
                    'sample_name': str(asset['path'].name),
                    'scenario': str(asset['case']['scenario']),
                    'success_delta': float(row['success']) - float(baseline.success),
                    'exp_delta': float(baseline.expansions) - float(row['expansions']),
                    'time_overhead_ratio': (float(row['time_ms']) - float(baseline.runtime_ms)) / max(float(baseline.runtime_ms), 1e-6),
                    'path_delta': (float(base_path) - float(cx_path)) if np.isfinite(float(base_path)) and np.isfinite(float(cx_path)) else float('nan'),
                }
                val_case_rows.append(case_row)
                family[str(asset['case']['scenario'])].append(case_row)
            val_summary = {
                'success_delta_pp': 100.0 * float(np.mean([r['success_delta'] for r in val_case_rows])) if val_case_rows else 0.0,
                'exp_delta': float(np.mean([r['exp_delta'] for r in val_case_rows])) if val_case_rows else 0.0,
                'time_overhead_ratio': float(np.mean([r['time_overhead_ratio'] for r in val_case_rows])) if val_case_rows else 0.0,
                'path_delta': float(np.nanmean([r['path_delta'] for r in val_case_rows])) if val_case_rows else float('nan'),
            }
            family_summary = {
                scenario: {
                    'exp_delta': float(np.mean([r['exp_delta'] for r in grp])),
                    'time_overhead_ratio': float(np.mean([r['time_overhead_ratio'] for r in grp])),
                }
                for scenario, grp in family.items()
            }
            trials.append({'params_obj': params_obj, 'memory': memory, 'val_summary': val_summary, 'family_summary': family_summary})
            print(f'[cx12:{variant}] trial={idx} params={params_obj} summary={val_summary}')

        chosen = _choose_trial(trials)
        chosen_params = chosen['params_obj']
        chosen_memory = chosen['memory']
        public_rows = []
        for dataset, assets, cap in [('exp3', public_assets_exp3, int(args.exp3_cap)), ('exp4', public_assets_exp4, int(args.exp4_cap))]:
            variant_rows = _eval_variant(mod, chosen_memory, chosen_params, predictor, cfg, assets, cap, args.device, f'{variant} (Full)')
            for row in variant_rows:
                row['dataset'] = dataset
            public_rows.extend(base_public_by_dataset[dataset])
            public_rows.extend(variant_rows)
            for spec in getattr(mod, 'ablation_specs', lambda: [])():
                ab_rows = []
                for idx, asset in enumerate(assets, start=1):
                    field = mod.build_nonholonomic_field(asset['case'], predictor, cfg, chosen_params, chosen_memory)
                    prep_t0 = time.perf_counter()
                    policy = mod.make_policy(chosen_memory, chosen_params, asset['case'], asset['bundle'], field, args.device, ablation=spec)
                    prep_ms = (time.perf_counter() - prep_t0) * 1000.0
                    plan = run_hybrid_with_policy(asset['case'], field, int(cap), successor_policy=policy, record_expanded=False)
                    ab_rows.append({
                        'sample_name': str(asset['path'].name),
                        'scenario': str(asset['case']['scenario']),
                        'method': f"{variant} ({spec['name']})",
                        'success': float(plan.success),
                        'expansions': float(plan.expansions),
                        'time_ms': float(plan.runtime_ms + prep_ms),
                        'path_length': float(_path_len(plan)),
                        'dataset': dataset,
                    })
                    if idx % 5 == 0 or idx == len(assets):
                        print(f"[{variant} ({spec['name']})] {idx}/{len(assets)}")
                public_rows.extend(ab_rows)
        _write_csv(out_root / 'public_case_rows.csv', public_rows)
        public_summary = _summary(public_rows, ('dataset', 'method'))
        public_delta = _delta(public_summary, ('dataset',), baseline_method='CX3-D')
        public_family = _family_delta(public_rows, ('dataset',), baseline_method='CX3-D')
        _write_csv(out_root / 'public_summary.csv', public_summary)
        _write_csv(out_root / 'public_delta.csv', public_delta)
        _write_csv(out_root / 'public_family_delta.csv', public_family)

        standard_rows = _standard_audit(mod, chosen_memory, chosen_params, predictor, args.benchmark_root, int(args.max_mp_cases), int(args.max_csm_cases))
        _write_csv(out_root / 'standard_field_audit.csv', standard_rows)

        chosen_json = {
            'variant': variant,
            'params': chosen_params.__dict__,
            'val_summary': chosen['val_summary'],
            'fit_dir': str(out_root),
            'train_rows': int(chosen_memory.get('train_rows', 0)),
            'out_root': str(out_root),
        }
        (out_root / 'chosen.json').write_text(json.dumps(chosen_json, indent=2, ensure_ascii=False), encoding='utf-8')
        inputs = [args.ours_checkpoint, args.teacher_chosen_json, args.base_chosen_json, args.split_root / 'calib_train.csv', args.split_root / 'calib_val.csv']
        inputs += train_files + val_files + guard_files + public_files
        write_inputs_sha256(inputs, out_root / 'inputs_sha256.json')
        manifest = {
            'version': 'rs_p0cx12_round1_v1',
            'runtime_hours': float((time.perf_counter() - t0) / 3600.0),
            'variant': variant,
            'chosen': chosen_json,
            'inputs_sha256': json.loads((out_root / 'inputs_sha256.json').read_text(encoding='utf-8')),
        }
        (out_root / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')

        val_family_rows = []
        for scenario, vals in sorted(chosen['family_summary'].items()):
            val_family_rows.append({
                'scenario': scenario,
                'success_delta_pp': 0.0,
                'exp_delta': float(vals['exp_delta']),
                'time_overhead_ratio': float(vals['time_overhead_ratio']),
            })
        exp4_variant = next((r for r in public_delta if r['dataset'] == 'exp4' and r['method'] == f'{variant} (Full)'), None)
        flange = next((r for r in public_family if r['dataset'] == 'exp4' and r['scenario'] == 'flange' and r['method'] == f'{variant} (Full)'), None)
        if exp4_variant is not None and flange is not None:
            passed = float(exp4_variant['exp_delta']) > 0.0 and float(exp4_variant['mean_time_overhead_ratio']) < 0.30 and float(flange['exp_delta']) >= 0.0
            if passed:
                readout = 'result: positive public trend with controlled overhead; candidate merits next-stage validation.'
            else:
                readout = 'result: public parasol gate is not cleared under the locked dev selection.'
        else:
            readout = 'result: missing public evaluation rows.'
        _write_report(report_path, f'{variant} Pilot V1', chosen_json, val_family_rows, public_delta, public_family, standard_rows, readout)
        summary_rows.append({
            'variant': variant,
            'chosen_params': chosen_params.__dict__,
            'calib_val_exp_delta': float(chosen['val_summary']['exp_delta']),
            'calib_val_overhead': float(chosen['val_summary']['time_overhead_ratio']),
            'exp4_exp_delta': float(exp4_variant['exp_delta']) if exp4_variant else float('nan'),
            'exp4_overhead': float(exp4_variant['mean_time_overhead_ratio']) if exp4_variant else float('nan'),
            'flange_exp_delta': float(flange['exp_delta']) if flange else float('nan'),
            'report_path': str(report_path),
            'out_root': str(out_root),
        })

    summary_root = args.outputs_root / 'rs_p0cx12_round1_summary'
    summary_root.mkdir(parents=True, exist_ok=True)
    _write_csv(summary_root / 'summary.csv', summary_rows)
    (summary_root / 'summary.json').write_text(json.dumps({'variants': summary_rows}, indent=2, ensure_ascii=False), encoding='utf-8')
    lines = [
        '# P0-CX12 Round1 Summary',
        '',
        '- protocol: base sketch locked from `CX10-D`; new CX12 layers trained on dev-only data and evaluated on public `parasol_narrow` after lock-in',
        '- no `rs_root_hard_v2/test` evidence was consumed in this round',
        '',
        '## Variant Readout',
    ]
    for row in summary_rows:
        lines.append(f"- `{row['variant']}`: calib_val exp_delta=`{row['calib_val_exp_delta']:.3f}`, calib_val overhead=`{row['calib_val_overhead']:.6f}`, exp4 exp_delta=`{row['exp4_exp_delta']:.3f}`, exp4 overhead=`{row['exp4_overhead']:.6f}`, flange exp_delta=`{row['flange_exp_delta']:.3f}`")
    ranked = sorted(summary_rows, key=lambda r: (float(r['exp4_exp_delta']), -float(r['exp4_overhead'])), reverse=True)
    lines += ['', '## Ordering']
    for idx, row in enumerate(ranked, start=1):
        lines.append(f"- rank {idx}: `{row['variant']}`")
    (args.reports_root / 'rs_p0cx12_round1_summary.md').write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    main()
