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
from rs_cx25.common import build_frozen_cx24_stack
from rs_cx21.common import run_hybrid_with_policy, standard_identity_error
from rs_cx8.common import load_nonholonomic_assets, load_nonholonomic_contexts, write_inputs_sha256

MODULES = {
    'CX25-B': 'rs_cx25.cx25_b_dto',
    'CX25-A': 'rs_cx25.cx25_a_ssc',
    'CX25-C': 'rs_cx25.cx25_c_clr',
    'CX25-D': 'rs_cx25.cx25_d_tsd',
    'CX25-E': 'rs_cx25.cx25_e_gsc',
}
SLUG = {'CX25-B': 'b', 'CX25-A': 'a', 'CX25-C': 'c', 'CX25-D': 'd', 'CX25-E': 'e'}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Run P0-CX25 round1 pilots.')
    p.add_argument('--variants', type=str, default='CX25-B,CX25-A,CX25-C,CX25-D,CX25-E')
    p.add_argument('--public-datasets', type=str, default='exp4')
    p.add_argument('--split-root', type=Path, default=Path('data/split/calib_hard_v1'))
    p.add_argument('--parasol-root', type=Path, default=Path('data/benchmark/parasol_narrow/test'))
    p.add_argument('--benchmark-root', type=Path, default=Path('data/benchmark'))
    p.add_argument('--ours-checkpoint', type=Path, default=Path('outputs/checkpoints/exp3_final_manual_v11b.pt'))
    p.add_argument('--device', type=str, default='cuda')
    p.add_argument('--dev-cap', type=int, default=20000)
    p.add_argument('--exp3-cap', type=int, default=7000)
    p.add_argument('--exp4-cap', type=int, default=20000)
    p.add_argument('--max-mp-cases', type=int, default=800)
    p.add_argument('--max-csm-cases', type=int, default=400)
    p.add_argument('--public-baseline-cache', type=Path, default=Path('outputs/rs_p0cx14_b_pilot_v1/public_case_rows.csv'))
    p.add_argument('--reports-root', type=Path, default=Path('reports'))
    p.add_argument('--outputs-root', type=Path, default=Path('outputs'))
    return p.parse_args()


def _variants(raw: str) -> list[str]:
    return [item.strip() for item in str(raw).split(',') if item.strip()]


def _datasets(raw: str) -> list[str]:
    return [item.strip() for item in str(raw).split(',') if item.strip()]


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


def _path_len(plan) -> float:
    arr = np.asarray(plan.path[:, :2], dtype=np.float32)
    if arr.shape[0] < 2:
        return float('nan')
    return float(np.sum(np.linalg.norm(arr[1:] - arr[:-1], axis=1)))


def _summary(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[tuple(row[k] for k in keys)].append(row)
    out = []
    for key, grp in sorted(grouped.items()):
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
        grouped[tuple(row[k] for k in group_keys)][str(row['method'])] = row
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
    def _flange(trial: dict[str, Any]) -> float:
        return float(trial['family_summary'].get('flange', {}).get('exp_delta', 0.0))
    ranked = sorted(
        trials,
        key=lambda t: (
            1 if _flange(t) >= 0.0 else 0,
            1 if float(t['val_summary']['exp_delta']) > 0.0 else 0,
            float(t['val_summary']['success_delta_pp']),
            float(t['val_summary']['exp_delta']),
            -float(t['val_summary']['time_overhead_ratio']),
        ),
        reverse=True,
    )
    return ranked[0]


def _eval_variant(mod, memory: dict[str, Any], params_obj: Any, predictor, cfg: CXGlobalConfig, assets: list[dict[str, Any]], cap: int, device: str, method_name: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = []
    diag_rows = []
    total = len(assets)
    for idx, asset in enumerate(assets, start=1):
        field = mod.build_nonholonomic_field(asset['case'], predictor, cfg, params_obj, memory)
        bundle = asset['case'].get('_cx21_bundle', asset['bundle'])
        prep_t0 = time.perf_counter()
        policy = mod.make_policy(memory, params_obj, asset['case'], bundle, field, device, ablation=None)
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
        if hasattr(policy, 'export_diagnostics'):
            for item in list(policy.export_diagnostics()):
                diag_rows.append({'sample_name': str(asset['path'].name), 'scenario': str(asset['case']['scenario']), 'method': method_name, **item})
        if idx % 5 == 0 or idx == total:
            print(f'[{method_name}] {idx}/{total}', flush=True)
    return rows, diag_rows


def _eval_ablation(mod, memory: dict[str, Any], params_obj: Any, predictor, cfg: CXGlobalConfig, assets: list[dict[str, Any]], cap: int, device: str, method_name: str, ablation: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    total = len(assets)
    for idx, asset in enumerate(assets, start=1):
        field = mod.build_nonholonomic_field(asset['case'], predictor, cfg, params_obj, memory)
        bundle = asset['case'].get('_cx21_bundle', asset['bundle'])
        prep_t0 = time.perf_counter()
        policy = mod.make_policy(memory, params_obj, asset['case'], bundle, field, device, ablation=ablation)
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
            print(f'[{method_name}] {idx}/{total}', flush=True)
    return rows


def _standard_audit(mod, memory: dict[str, Any], params_obj: Any, predictor, benchmark_root: Path, max_mp_cases: int, max_csm_cases: int) -> list[dict[str, Any]]:
    rows = []
    for dataset, limit in [('mp', int(max_mp_cases)), ('csm', int(max_csm_cases))]:
        files = sorted((benchmark_root / dataset / 'test').glob('sample_*.npz'))[:limit]
        diffs = []
        for idx, path in enumerate(files, start=1):
            sample = load_grid_sample(path)
            diffs.append(standard_identity_error(sample, predictor, lambda s, p: mod.build_standard_field(s, p, params_obj, memory)))
            if idx % 100 == 0 or idx == len(files):
                print(f'[cx25:standard:{dataset}] {idx}/{len(files)}', flush=True)
        rows.append({
            'dataset': dataset,
            'num_cases': int(len(files)),
            'max_abs_field_diff': float(max(diffs) if diffs else 0.0),
            'mean_abs_field_diff': float(np.mean(diffs) if diffs else 0.0),
        })
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


def _variant_report(path: Path, title: str, chosen_json: dict[str, Any], val_family_rows: list[dict[str, Any]], public_delta: list[dict[str, Any]], public_family: list[dict[str, Any]], standard_rows: list[dict[str, Any]], *, observatory_note: str | None = None) -> None:
    lines = [
        f'# {title}',
        '',
        '- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; this round intentionally stayed public-first and did not consume hard-test evidence',
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
        lines.append(f"- `{row['scenario']}`: exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['time_overhead_ratio']):.6f}`")
    lines += ['', '## Public Parasol vs `CX3-D`']
    for row in public_delta:
        lines.append(f"- `{row['dataset']}` / `{row['method']}`: success_delta_pp=`{float(row['success_delta_pp']):.3f}`, exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`")
    lines += ['', '## Public `exp4` Family Breakdown']
    for row in public_family:
        if row['dataset'] == 'exp4':
            lines.append(f"- `{row['scenario']}` / `{row['method']}`: success_delta_pp=`{float(row['success_delta_pp']):.3f}`, exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`")
    lines += ['', '## Hard Benchmark vs `CX3-D`', '- skipped: this round intentionally stayed public-first / ordinary-support; no hard-test evidence was consumed.', '', '## Hard Family Breakdown', '- skipped: this round intentionally stayed public-first / ordinary-support; no hard-test evidence was consumed.']
    if observatory_note:
        lines += ['', '## Observatory', f'- {observatory_note}']
    lines += ['', '## Standard Support Audit']
    for row in standard_rows:
        lines.append(f"- `{row['dataset']}`: num_cases=`{row['num_cases']}`, max_abs_field_diff=`{float(row['max_abs_field_diff']):.6f}`, mean_abs_field_diff=`{float(row['mean_abs_field_diff']):.6f}`")
    path.write_text('\n'.join(lines), encoding='utf-8')


def main() -> None:
    args = parse_args()
    args.reports_root.mkdir(parents=True, exist_ok=True)
    args.outputs_root.mkdir(parents=True, exist_ok=True)
    variants = _variants(args.variants)
    public_datasets = _datasets(args.public_datasets)

    predictor = NeuralHeuristicPredictor(args.ours_checkpoint, device=args.device, gaussian_sigma=2.5)
    cfg = CXGlobalConfig()

    train_rows_data = _read_split_rows(args.split_root / 'calib_train.csv')
    val_rows_data = _read_split_rows(args.split_root / 'calib_val.csv')
    train_files = [Path(r['path']) for r in train_rows_data]
    val_files = [Path(r['path']) for r in val_rows_data]
    public_files = sorted(args.parasol_root.glob('sample_*.npz'))

    train_assets = load_nonholonomic_assets(train_files, predictor, cfg, int(args.dev_cap), tag='cx25:calib-train')
    val_contexts = load_nonholonomic_contexts(val_files, predictor, cfg, tag='cx25:calib-val')
    public_contexts = load_nonholonomic_contexts(public_files, predictor, cfg, tag='cx25:public')

    stack = build_frozen_cx24_stack(train_assets, val_contexts, predictor, cfg, args.device, args.outputs_root / 'rs_p0cx25_stack_cache')
    dependencies = {'cx24_stack': stack}

    summary_rows = []
    standard_audit_rows = []

    for variant in variants:
        mod = importlib.import_module(MODULES[variant])
        slug = SLUG[variant]
        out_root = args.outputs_root / f'rs_p0cx25_{slug}_pilot_v1'
        out_root.mkdir(parents=True, exist_ok=True)
        report_path = args.reports_root / f'rs_p0cx25_{slug}_pilot_v1.md'
        trials = []
        for idx, params_obj in enumerate(mod.param_grid(), start=1):
            fit_dir = out_root / 'trials' / f'trial_{idx:02d}'
            memory = mod.fit_variant(train_assets, val_contexts, predictor, cfg, params_obj, fit_dir, args.device, dependencies)
            val_rows, _ = _eval_variant(mod, memory, params_obj, predictor, cfg, val_contexts, int(args.dev_cap), args.device, f'{variant} (Candidate)')
            val_case_rows = []
            family = defaultdict(list)
            for row_data, asset, row in zip(val_rows_data, val_contexts, val_rows):
                base_success = float(row_data['success'])
                base_expansions = float(row_data['expansions'])
                base_runtime_ms = float(row_data['runtime_ms'])
                base_path = float(row_data['path_length'])
                cx_path = float(row['path_length']) if np.isfinite(float(row['path_length'])) else float('nan')
                case_row = {
                    'sample_name': str(asset['path'].name),
                    'scenario': str(asset['case']['scenario']),
                    'success_delta': float(row['success']) - float(base_success),
                    'exp_delta': float(base_expansions) - float(row['expansions']),
                    'time_overhead_ratio': (float(row['time_ms']) - float(base_runtime_ms)) / max(float(base_runtime_ms), 1e-6),
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
            family_summary = {scenario: {'exp_delta': float(np.mean([r['exp_delta'] for r in grp])), 'time_overhead_ratio': float(np.mean([r['time_overhead_ratio'] for r in grp]))} for scenario, grp in family.items()}
            trials.append({'params_obj': params_obj, 'memory': memory, 'val_summary': val_summary, 'family_summary': family_summary})
            print(f'[cx25:{variant}] trial={idx} params={params_obj} summary={val_summary}', flush=True)

        chosen = _choose_trial(trials)
        chosen_params = chosen['params_obj']
        chosen_memory = chosen['memory']

        public_rows = []
        diagnostic_rows = []
        for dataset in public_datasets:
            public_rows.extend(_cached_baseline_rows(args.public_baseline_cache, dataset=dataset))
        for dataset in public_datasets:
            cap = int(args.exp3_cap) if dataset == 'exp3' else int(args.exp4_cap)
            variant_rows, diag_rows = _eval_variant(mod, chosen_memory, chosen_params, predictor, cfg, public_contexts, int(cap), args.device, f'{variant} (Full)')
            for row in variant_rows:
                row['dataset'] = dataset
            for row in diag_rows:
                row['dataset'] = dataset
            public_rows.extend(variant_rows)
            diagnostic_rows.extend(diag_rows)
            if dataset == 'exp4':
                for spec in getattr(mod, 'ablation_specs', lambda: [])():
                    ab_rows = _eval_ablation(mod, chosen_memory, chosen_params, predictor, cfg, public_contexts, int(cap), args.device, f"{variant} ({spec['name']})", spec)
                    for row in ab_rows:
                        row['dataset'] = dataset
                    public_rows.extend(ab_rows)
        _write_csv(out_root / 'public_case_rows.csv', public_rows)
        if diagnostic_rows:
            _write_csv(out_root / 'diagnostic_rows.csv', diagnostic_rows)
        public_summary = _summary(public_rows, ('dataset', 'method'))
        public_delta = _delta(public_summary, ('dataset',), baseline_method='CX3-D')
        public_family = _family_delta(public_rows, ('dataset',), baseline_method='CX3-D')
        _write_csv(out_root / 'public_summary.csv', public_summary)
        _write_csv(out_root / 'public_delta.csv', public_delta)
        _write_csv(out_root / 'public_family_delta.csv', public_family)

        observatory_note = None
        if diagnostic_rows:
            state_counts = defaultdict(int)
            for row in diagnostic_rows:
                state_counts[str(row.get('auto_state', 'observe'))] += 1
            observatory_note = f"diagnostic rows saved to `outputs/rs_p0cx25_{slug}_pilot_v1/diagnostic_rows.csv`; state_counts=`{dict(state_counts)}`"

        standard_rows = _standard_audit(mod, chosen_memory, chosen_params, predictor, args.benchmark_root, int(args.max_mp_cases), int(args.max_csm_cases))
        _write_csv(out_root / 'standard_field_audit.csv', standard_rows)
        for row in standard_rows:
            standard_audit_rows.append({'variant': variant, **row})

        chosen_json = {'variant': variant, 'params': chosen_params.__dict__, 'val_summary': chosen['val_summary'], 'out_root': str(out_root)}
        (out_root / 'chosen.json').write_text(json.dumps(chosen_json, indent=2, ensure_ascii=False), encoding='utf-8')
        inputs = [args.ours_checkpoint, args.split_root / 'calib_train.csv', args.split_root / 'calib_val.csv']
        inputs += train_files + val_files + public_files
        write_inputs_sha256(inputs, out_root / 'inputs_sha256.json')

        val_family_rows = [{'scenario': scenario, 'exp_delta': float(vals['exp_delta']), 'time_overhead_ratio': float(vals['time_overhead_ratio'])} for scenario, vals in sorted(chosen['family_summary'].items())]
        _variant_report(report_path, f'{variant} Pilot V1', chosen_json, val_family_rows, public_delta, public_family, standard_rows, observatory_note=observatory_note)

        full_exp4 = next((r for r in public_delta if r['dataset'] == 'exp4' and r['method'] == f'{variant} (Full)'), None)
        flange = next((r for r in public_family if r['dataset'] == 'exp4' and r['method'] == f'{variant} (Full)' and r['scenario'] == 'flange'), None)
        summary_rows.append({
            'variant': variant,
            'chosen_params': chosen_params.__dict__,
            'calib_val_exp_delta': float(chosen['val_summary']['exp_delta']),
            'calib_val_overhead': float(chosen['val_summary']['time_overhead_ratio']),
            'exp4_exp_delta': float(full_exp4['exp_delta']) if full_exp4 else float('nan'),
            'exp4_overhead': float(full_exp4['mean_time_overhead_ratio']) if full_exp4 else float('nan'),
            'flange_exp_delta': float(flange['exp_delta']) if flange else float('nan'),
            'report_path': str(report_path),
            'out_root': str(out_root),
        })

    summary_root = args.outputs_root / 'rs_p0cx25_round1_summary'
    summary_root.mkdir(parents=True, exist_ok=True)
    _write_csv(summary_root / 'summary.csv', summary_rows)
    (summary_root / 'summary.json').write_text(json.dumps({'variants': summary_rows}, indent=2, ensure_ascii=False), encoding='utf-8')
    lines = [
        '# P0-CX25 Round1 Summary',
        '',
        '- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; this round stayed public-first and did not consume hard-test evidence',
        '',
        '## Variant Readout',
    ]
    for row in summary_rows:
        lines.append(f"- `{row['variant']}`: calib_val exp_delta=`{row['calib_val_exp_delta']:.3f}`, calib_val overhead=`{row['calib_val_overhead']:.6f}`, exp4 exp_delta=`{row['exp4_exp_delta']:.3f}`, exp4 overhead=`{row['exp4_overhead']:.6f}`, flange exp_delta=`{row['flange_exp_delta']:.3f}`")
    ranked = sorted(summary_rows, key=lambda r: (-float(r['exp4_exp_delta']), float(r['exp4_overhead'])))
    lines += ['', '## Ordering']
    for idx, row in enumerate(ranked, start=1):
        lines.append(f"- rank {idx}: `{row['variant']}`")
    (args.reports_root / 'rs_p0cx25_round1_summary.md').write_text('\n'.join(lines), encoding='utf-8')

    audit_lines = ['# P0-CX25 Standard Audit V1', '', '- protocol: ordinary-support audit checks `build_standard_field == accepted CX3-D` by construction', '']
    for row in standard_audit_rows:
        audit_lines.append(f"- `{row['variant']}` / `{row['dataset']}`: num_cases=`{row['num_cases']}`, max_abs_field_diff=`{float(row['max_abs_field_diff']):.6f}`, mean_abs_field_diff=`{float(row['mean_abs_field_diff']):.6f}`")
    (args.reports_root / 'rs_p0cx25_standard_audit_v1.md').write_text('\n'.join(audit_lines), encoding='utf-8')


if __name__ == '__main__':
    main()
