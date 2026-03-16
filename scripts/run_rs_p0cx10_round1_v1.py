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
from rs_cx10.common import accepted_cx3d_standard, load_teacher_memory, run_hybrid_with_policy
from rs_cx8.common import load_nonholonomic_assets, write_inputs_sha256

MODULES = {
    'CX10-A': 'rs_cx10.cx10_a_cec',
    'CX10-B': 'rs_cx10.cx10_b_hbc',
    'CX10-C': 'rs_cx10.cx10_c_nfa',
    'CX10-D': 'rs_cx10.cx10_d_las',
}
VARIANT_SLUG = {
    'CX10-A': 'a',
    'CX10-B': 'b',
    'CX10-C': 'c',
    'CX10-D': 'd',
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Run P0-CX10 compiled-semantics suite.')
    p.add_argument('--variants', type=str, default='CX10-A,CX10-B,CX10-C,CX10-D')
    p.add_argument('--split-root', type=Path, default=Path('data/split/calib_hard_v1'))
    p.add_argument('--benchmark-root', type=Path, default=Path('data/benchmark'))
    p.add_argument('--parasol-root', type=Path, default=Path('data/benchmark/parasol_narrow/test'))
    p.add_argument('--hard-benchmark-root', type=Path, default=Path('data/benchmark/rs_root_hard_v2'))
    p.add_argument('--ours-checkpoint', type=Path, default=Path('outputs/checkpoints/exp3_final_manual_v11b.pt'))
    p.add_argument('--teacher-chosen-json', type=Path, default=Path('outputs/rs_p0cx8_d_hard_pilot_v1/chosen.json'))
    p.add_argument('--device', type=str, default='cuda')
    p.add_argument('--dev-cap', type=int, default=20000)
    p.add_argument('--exp3-cap', type=int, default=7000)
    p.add_argument('--exp4-cap', type=int, default=20000)
    p.add_argument('--hard-cap', type=int, default=20000)
    p.add_argument('--max-mp-cases', type=int, default=800)
    p.add_argument('--max-csm-cases', type=int, default=400)
    p.add_argument('--skip-hard', action='store_true')
    p.add_argument('--skip-standard-audit', action='store_true')
    p.add_argument('--reports-root', type=Path, default=Path('reports'))
    p.add_argument('--outputs-root', type=Path, default=Path('outputs'))
    return p.parse_args()


def _variants(raw: str) -> list[str]:
    return [item.strip() for item in str(raw).split(',') if item.strip()]


def _read_split_csv(path: Path) -> list[Path]:
    with path.open('r', newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    return [Path(row['path']) for row in rows]


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
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _path_len(plan) -> float:
    arr = np.asarray(plan.path[:, :2], dtype=np.float32) if hasattr(plan, 'path') else np.asarray(plan, dtype=np.float32)
    if arr.shape[0] < 2:
        return float('nan')
    return float(np.sum(np.linalg.norm(arr[1:] - arr[:-1], axis=1)))


def _choose_trial(trials: list[dict[str, Any]]) -> dict[str, Any]:
    feasible = [t for t in trials if float(t['val_summary']['time_overhead_ratio']) <= 0.30]
    ranked = feasible if feasible else trials
    ranked.sort(
        key=lambda t: (
            float(t['val_summary']['success_delta_pp']),
            float(t['val_summary']['exp_delta']),
            -float(t['val_summary']['time_overhead_ratio']),
            float(t['val_summary']['path_delta']) if np.isfinite(float(t['val_summary']['path_delta'])) else 0.0,
        ),
        reverse=True,
    )
    return ranked[0]


def _summary(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    by: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by[tuple(row[k] for k in keys)].append(row)
    out = []
    for key, grp in sorted(by.items()):
        item = {k: key[i] for i, k in enumerate(keys)}
        item.update({
            'num_cases': int(len(grp)),
            'success_rate': float(np.mean([float(r['success']) for r in grp])) if grp else 0.0,
            'avg_expansions': float(np.mean([float(r['expansions']) for r in grp])) if grp else 0.0,
            'avg_time_ms': float(np.mean([float(r['time_ms']) for r in grp])) if grp else 0.0,
            'avg_prep_ms': float(np.mean([float(r.get('prep_time_ms', 0.0)) for r in grp])) if grp else 0.0,
            'avg_path_length': float(np.nanmean([float(r['path_length']) for r in grp])) if grp else float('nan'),
        })
        out.append(item)
    return out


def _delta(summary_rows: list[dict[str, Any]], group_keys: tuple[str, ...], baseline_method: str = 'CX3-D') -> list[dict[str, Any]]:
    by_group: dict[tuple[Any, ...], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in summary_rows:
        grp = tuple(row[k] for k in group_keys)
        by_group[grp][str(row['method'])] = row
    out = []
    for grp, methods in sorted(by_group.items()):
        base = methods.get(baseline_method, None)
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


def _attach_rs_assets(assets: list[dict[str, Any]], cap: int, tag: str) -> None:
    for i, asset in enumerate(assets, start=1):
        if 'rs_result' not in asset:
            asset['rs_result'] = run_hybrid_with_policy(asset['case'], asset['bundle']['rs_base'], int(cap), successor_policy=None, record_expanded=False)
        if i % 10 == 0 or i == len(assets):
            print(f'[{tag}] rs baseline {i}/{len(assets)}')


def _eval_variant_on_assets(mod, memory: dict[str, Any], params_obj: Any, predictor, cfg: CXGlobalConfig, assets: list[dict[str, Any]], cap: int, methods: list[tuple[str, dict[str, Any] | None]], dataset_name: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, asset in enumerate(assets, start=1):
        case = asset['case']
        bundle = asset['bundle']
        baseline = asset['baseline_result']
        rs_plan = asset['rs_result']
        base_path = _path_len(baseline)
        rs_path = _path_len(rs_plan)
        rows.append({
            'dataset': dataset_name,
            'sample_name': asset['path'].name,
            'scenario': str(case['scenario']),
            'method': 'Hybrid A* (RS)',
            'success': float(rs_plan.success),
            'expansions': float(rs_plan.expansions),
            'time_ms': float(rs_plan.runtime_ms),
            'prep_time_ms': 0.0,
            'path_length': float(rs_path),
        })
        rows.append({
            'dataset': dataset_name,
            'sample_name': asset['path'].name,
            'scenario': str(case['scenario']),
            'method': 'CX3-D',
            'success': float(baseline.success),
            'expansions': float(baseline.expansions),
            'time_ms': float(baseline.runtime_ms),
            'prep_time_ms': 0.0,
            'path_length': float(base_path),
        })
        field = mod.build_nonholonomic_field(case, predictor, cfg, params_obj, memory)
        for method_name, ablation in methods:
            prep_t0 = time.perf_counter()
            policy = mod.make_policy(memory, params_obj, case, bundle, field, str(getattr(predictor, 'device', 'cpu')), ablation=ablation)
            prep_ms = (time.perf_counter() - prep_t0) * 1000.0
            plan = run_hybrid_with_policy(case, field, int(cap), successor_policy=policy, record_expanded=False)
            rows.append({
                'dataset': dataset_name,
                'sample_name': asset['path'].name,
                'scenario': str(case['scenario']),
                'method': method_name,
                'success': float(plan.success),
                'expansions': float(plan.expansions),
                'time_ms': float(plan.runtime_ms + prep_ms),
                'prep_time_ms': float(prep_ms),
                'path_length': float(_path_len(plan)),
            })
        if idx % 5 == 0 or idx == len(assets):
            print(f'[{dataset_name}:{method_name}] {idx}/{len(assets)}')
    return rows


def _write_variant_report(
    report_path: Path,
    variant: str,
    chosen_json: dict[str, Any],
    val_family_rows: list[dict[str, Any]],
    public_delta_rows: list[dict[str, Any]],
    public_family_delta: list[dict[str, Any]],
    hard_delta_rows: list[dict[str, Any]],
    standard_audit_rows: list[dict[str, Any]],
) -> None:
    lines = [
        f'# {variant} Pilot V1',
        '',
        '- protocol: params selected on `data/split/calib_hard_v1` only; public/hard benchmarks were run after lock-in',
        f"- chosen params: `{chosen_json['params']}`",
        '',
        '## Calib Val vs accepted `CX3-D`',
        f"- success_delta_pp=`{chosen_json['val_summary']['success_delta_pp']:.3f}`",
        f"- exp_delta=`{chosen_json['val_summary']['exp_delta']:.3f}`",
        f"- mean_time_overhead_ratio=`{chosen_json['val_summary']['time_overhead_ratio']:.6f}`",
        f"- path_delta=`{chosen_json['val_summary']['path_delta']:.3f}`",
        '',
        '## Calib Family Breakdown',
    ]
    for row in val_family_rows:
        lines.append(f"- `{row['scenario']}`: success_delta_pp=`{row['success_delta_pp']:.3f}`, exp_delta=`{row['exp_delta']:.3f}`, mean_time_overhead_ratio=`{row['time_overhead_ratio']:.6f}`")
    lines += ['', '## Public Parasol vs `CX3-D`']
    for row in sorted(public_delta_rows, key=lambda r: (str(r['dataset']), str(r['method']))):
        lines.append(f"- `{row['dataset']}` / `{row['method']}`: success_delta_pp=`{row['success_delta_pp']:.3f}`, exp_delta=`{row['exp_delta']:.3f}`, mean_time_overhead_ratio=`{row['mean_time_overhead_ratio']:.6f}`")
    lines += ['', '## Public Family Delta vs `CX3-D`']
    for row in sorted(public_family_delta, key=lambda r: (str(r['dataset']), str(r['scenario']), str(r['method']))):
        lines.append(f"- `{row['dataset']}` / `{row['scenario']}` / `{row['method']}`: success_delta_pp=`{row['success_delta_pp']:.3f}`, exp_delta=`{row['exp_delta']:.3f}`, mean_time_overhead_ratio=`{row['mean_time_overhead_ratio']:.6f}`")
    if hard_delta_rows:
        lines += ['', '## Auxiliary Hard Benchmark vs `CX3-D`']
        for row in sorted(hard_delta_rows, key=lambda r: str(r['method'])):
            lines.append(f"- `{row['method']}`: success_delta_pp=`{row['success_delta_pp']:.3f}`, exp_delta=`{row['exp_delta']:.3f}`, mean_time_overhead_ratio=`{row['mean_time_overhead_ratio']:.6f}`")
    if standard_audit_rows:
        lines += ['', '## Standard Support Audit']
        for row in standard_audit_rows:
            lines.append(f"- `{row['dataset']}`: num_cases=`{row['num_cases']}`, max_abs_field_diff=`{row['max_abs_field_diff']:.6f}`, mean_abs_field_diff=`{row['mean_abs_field_diff']:.6f}`")
    public_full = [r for r in public_delta_rows if str(r['method']).endswith('(Full)')]
    lines += ['', '## Readout']
    if public_full and all(float(r['exp_delta']) > 0.0 for r in public_full):
        lines.append('- result: public parasol benchmark shows a positive expansion trend against accepted `CX3-D`.')
    else:
        lines.append('- result: public parasol benchmark does not yet show a stable positive expansion trend against accepted `CX3-D`.')
    report_path.write_text('\n'.join(lines), encoding='utf-8')


def _standard_field_audit(mod, memory: dict[str, Any], params_obj: Any, predictor, standard_samples: dict[str, list[Any]]) -> list[dict[str, Any]]:
    rows = []
    for dataset, samples in [('mp', list(standard_samples.get('mp', []))), ('csm', list(standard_samples.get('csm', [])) )]:
        max_diff = 0.0
        diffs = []
        for idx, sample in enumerate(samples, start=1):
            _, accepted = accepted_cx3d_standard(sample, predictor)
            field = mod.build_standard_field(sample, predictor, params_obj, memory)
            diff = float(np.max(np.abs(np.asarray(field, dtype=np.float32) - np.asarray(accepted, dtype=np.float32))))
            max_diff = max(max_diff, diff)
            diffs.append(diff)
            if idx % 100 == 0 or idx == len(samples):
                print(f'[standard-audit:{dataset}] {idx}/{len(samples)}')
        rows.append({
            'dataset': dataset,
            'num_cases': int(len(samples)),
            'max_abs_field_diff': float(max_diff),
            'mean_abs_field_diff': float(np.mean(diffs)) if diffs else 0.0,
        })
    return rows


def main() -> None:
    args = parse_args()
    args.reports_root.mkdir(parents=True, exist_ok=True)
    args.outputs_root.mkdir(parents=True, exist_ok=True)
    variants = _variants(args.variants)
    predictor = NeuralHeuristicPredictor(args.ours_checkpoint, device=args.device, gaussian_sigma=2.5)
    cfg = CXGlobalConfig()
    teacher_memory = load_teacher_memory(args.teacher_chosen_json, args.device)
    teacher_memory['device'] = str(args.device)

    train_files = _read_split_csv(args.split_root / 'calib_train.csv')
    val_files = _read_split_csv(args.split_root / 'calib_val.csv')
    train_assets = load_nonholonomic_assets(train_files, predictor, cfg, int(args.dev_cap), tag='rs-p0cx10:train')
    val_assets = load_nonholonomic_assets(val_files, predictor, cfg, int(args.dev_cap), tag='rs-p0cx10:val')

    public_assets = {}
    for tag, cap in [('exp3', int(args.exp3_cap)), ('exp4', int(args.exp4_cap))]:
        files = sorted(args.parasol_root.glob('sample_*.npz'))
        assets = load_nonholonomic_assets(files, predictor, cfg, int(cap), tag=f'rs-p0cx10:{tag}')
        _attach_rs_assets(assets, int(cap), tag=f'rs-p0cx10:{tag}')
        public_assets[tag] = assets


    standard_samples = {'mp': [], 'csm': []}
    if not args.skip_standard_audit:
        standard_samples = {
            'mp': [load_grid_sample(p) for p in sorted((args.benchmark_root / 'mp' / 'test').glob('sample_*.npz'))[: int(args.max_mp_cases)]],
            'csm': [load_grid_sample(p) for p in sorted((args.benchmark_root / 'csm' / 'test').glob('sample_*.npz'))[: int(args.max_csm_cases)]],
        }

    hard_assets = None
    if not args.skip_hard:
        hard_files = sorted((args.hard_benchmark_root / 'test').glob('sample_*.npz'))
        hard_assets = load_nonholonomic_assets(hard_files, predictor, cfg, int(args.hard_cap), tag='rs-p0cx10:hard')
        _attach_rs_assets(hard_assets, int(args.hard_cap), tag='rs-p0cx10:hard')

    suite_summary = []
    t0 = time.perf_counter()
    for variant in variants:
        slug = VARIANT_SLUG[variant]
        mod = importlib.import_module(MODULES[variant])
        out_root = args.outputs_root / f'rs_p0cx10_{slug}_pilot_v1'
        out_root.mkdir(parents=True, exist_ok=True)
        report_path = args.reports_root / f'rs_p0cx10_{slug}_pilot_v1.md'
        trial_root = out_root / 'trials'
        trials = []
        dependencies = {
            'teacher_memory': teacher_memory,
            'teacher_chosen_json': args.teacher_chosen_json,
        }
        for idx, params_obj in enumerate(mod.param_grid(), start=1):
            fit_dir = trial_root / f'trial_{idx:02d}'
            memory = mod.fit_variant(train_assets, val_assets, predictor, cfg, params_obj, fit_dir, args.device, dependencies=dependencies)
            case_rows = []
            for asset in val_assets:
                baseline = asset['baseline_result']
                prep_t0 = time.perf_counter()
                field = mod.build_nonholonomic_field(asset['case'], predictor, cfg, params_obj, memory)
                policy = mod.make_policy(memory, params_obj, asset['case'], asset['bundle'], field, args.device, ablation=None)
                prep_ms = (time.perf_counter() - prep_t0) * 1000.0
                plan = run_hybrid_with_policy(asset['case'], field, int(args.dev_cap), successor_policy=policy, record_expanded=False)
                base_path = _path_len(baseline)
                cx_path = _path_len(plan)
                total_ms = float(plan.runtime_ms + prep_ms)
                case_rows.append({
                    'sample_name': asset['path'].name,
                    'scenario': str(asset['case']['scenario']),
                    'baseline_success': float(baseline.success),
                    'baseline_expansions': float(baseline.expansions),
                    'baseline_time_ms': float(baseline.runtime_ms),
                    'baseline_path_length': float(base_path),
                    'cx_success': float(plan.success),
                    'cx_expansions': float(plan.expansions),
                    'cx_time_ms': float(total_ms),
                    'cx_path_length': float(cx_path),
                    'prep_time_ms': float(prep_ms),
                    'success_delta': float(plan.success) - float(baseline.success),
                    'exp_delta': float(baseline.expansions) - float(plan.expansions),
                    'time_delta_ms': float(baseline.runtime_ms) - float(total_ms),
                    'time_overhead_ratio': (float(total_ms) - float(baseline.runtime_ms)) / max(float(baseline.runtime_ms), 1e-6),
                    'path_delta': (float(base_path) - float(cx_path)) if np.isfinite(float(base_path)) and np.isfinite(float(cx_path)) else float('nan'),
                })
            val_summary = {
                'success_delta_pp': 100.0 * float(np.mean([r['success_delta'] for r in case_rows])) if case_rows else 0.0,
                'exp_delta': float(np.mean([r['exp_delta'] for r in case_rows])) if case_rows else 0.0,
                'time_delta_ms': float(np.mean([r['time_delta_ms'] for r in case_rows])) if case_rows else 0.0,
                'time_overhead_ratio': float(np.mean([r['time_overhead_ratio'] for r in case_rows])) if case_rows else 0.0,
                'path_delta': float(np.nanmean([r['path_delta'] for r in case_rows])) if case_rows else float('nan'),
            }
            trials.append({'params_obj': params_obj, 'memory': memory, 'fit_dir': fit_dir, 'case_rows': case_rows, 'val_summary': val_summary})
            print(f'[rs-p0cx10:{variant}] trial={idx} params={params_obj} summary={val_summary}')

        chosen = _choose_trial(trials)
        chosen_json = {
            'variant': variant,
            'params': chosen['params_obj'].__dict__,
            'val_summary': chosen['val_summary'],
            'fit_dir': str(chosen['fit_dir']),
            'best_val_loss': float(chosen['memory'].get('best_val_loss', float('nan'))),
        }
        if 'train_rows' in chosen['memory']:
            chosen_json['train_rows'] = int(chosen['memory']['train_rows'])
        (out_root / 'chosen.json').write_text(json.dumps(chosen_json, indent=2, ensure_ascii=False), encoding='utf-8')
        _write_csv(out_root / 'calib_val_case_rows.csv', chosen['case_rows'])
        val_family_rows = []
        by = defaultdict(list)
        for row in chosen['case_rows']:
            by[str(row['scenario'])].append(row)
        for scenario, grp in sorted(by.items()):
            val_family_rows.append({
                'scenario': scenario,
                'num_cases': int(len(grp)),
                'success_delta_pp': 100.0 * float(np.mean([r['success_delta'] for r in grp])),
                'exp_delta': float(np.mean([r['exp_delta'] for r in grp])),
                'time_overhead_ratio': float(np.mean([r['time_overhead_ratio'] for r in grp])),
                'prep_time_ms': float(np.mean([r['prep_time_ms'] for r in grp])),
            })
        _write_csv(out_root / 'calib_val_family_rows.csv', val_family_rows)

        method_specs = [(f'{variant} (Full)', None)]
        for spec in getattr(mod, 'ablation_specs', lambda: [])():
            method_specs.append((f"{variant} ({spec['name']})", spec))

        public_rows = []
        for budget_name, assets in public_assets.items():
            rows = _eval_variant_on_assets(mod, chosen['memory'], chosen['params_obj'], predictor, cfg, assets, int(args.exp3_cap if budget_name == 'exp3' else args.exp4_cap), method_specs, budget_name)
            public_rows.extend(rows)
        _write_csv(out_root / 'public_case_rows.csv', public_rows)
        public_summary = _summary(public_rows, ('dataset', 'method'))
        public_delta = _delta(public_summary, ('dataset',), baseline_method='CX3-D')
        public_family_delta = _family_delta(public_rows, ('dataset',), baseline_method='CX3-D')
        _write_csv(out_root / 'public_summary.csv', public_summary)
        _write_csv(out_root / 'public_delta.csv', public_delta)
        _write_csv(out_root / 'public_family_delta.csv', public_family_delta)

        hard_delta = []
        if hard_assets is not None:
            hard_rows = _eval_variant_on_assets(mod, chosen['memory'], chosen['params_obj'], predictor, cfg, hard_assets, int(args.hard_cap), [(f'{variant} (Full)', None)], 'hard_test')
            _write_csv(out_root / 'hard_case_rows.csv', hard_rows)
            hard_summary = _summary(hard_rows, ('dataset', 'method'))
            hard_delta = _delta(hard_summary, ('dataset',), baseline_method='CX3-D')
            _write_csv(out_root / 'hard_summary.csv', hard_summary)
            _write_csv(out_root / 'hard_delta.csv', hard_delta)

        standard_rows = []
        if not args.skip_standard_audit:
            standard_rows = _standard_field_audit(mod, chosen['memory'], chosen['params_obj'], predictor, standard_samples)
            _write_csv(out_root / 'standard_field_audit.csv', standard_rows)

        inputs = [args.ours_checkpoint, args.teacher_chosen_json, args.split_root / 'manifest.json', args.split_root / 'calib_train.csv', args.split_root / 'calib_val.csv']
        inputs += train_files + val_files
        inputs += sorted(args.parasol_root.glob('sample_*.npz'))
        if hard_assets is not None:
            inputs += sorted((args.hard_benchmark_root / 'test').glob('sample_*.npz'))
        write_inputs_sha256(inputs, out_root / 'inputs_sha256.json')
        manifest = {
            'version': 'rs_p0cx10_round1_v1',
            'variant': variant,
            'runtime_hours': float((time.perf_counter() - t0) / 3600.0),
            'split_root': str(args.split_root),
            'teacher_chosen_json': str(args.teacher_chosen_json),
            'chosen': chosen_json,
            'inputs_sha256': json.loads((out_root / 'inputs_sha256.json').read_text(encoding='utf-8')),
        }
        (out_root / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
        _write_variant_report(report_path, variant, chosen_json, val_family_rows, public_delta, public_family_delta, hard_delta, standard_rows)

        exp4_full = next((r for r in public_delta if r['dataset'] == 'exp4' and r['method'] == f'{variant} (Full)'), None)
        hard_full = next((r for r in hard_delta if r['dataset'] == 'hard_test' and r['method'] == f'{variant} (Full)'), None)
        suite_summary.append({
            'variant': variant,
            'chosen_params': chosen_json['params'],
            'calib_val_exp_delta': float(chosen_json['val_summary']['exp_delta']),
            'calib_val_overhead': float(chosen_json['val_summary']['time_overhead_ratio']),
            'exp4_exp_delta': float(exp4_full['exp_delta']) if exp4_full else float('nan'),
            'exp4_overhead': float(exp4_full['mean_time_overhead_ratio']) if exp4_full else float('nan'),
            'hard_exp_delta': float(hard_full['exp_delta']) if hard_full else float('nan'),
            'hard_overhead': float(hard_full['mean_time_overhead_ratio']) if hard_full else float('nan'),
            'report_path': str(report_path),
            'out_root': str(out_root),
        })

    summary_root = args.outputs_root / 'rs_p0cx10_round1_summary'
    summary_root.mkdir(parents=True, exist_ok=True)
    _write_csv(summary_root / 'summary.csv', suite_summary)
    (summary_root / 'summary.json').write_text(json.dumps({'variants': suite_summary}, indent=2, ensure_ascii=False), encoding='utf-8')
    summary_lines = [
        '# P0-CX10 Round1 Summary',
        '',
        '- protocol: all variants selected on `calib_hard_v1` only; public and hard benchmarks were run after lock-in',
        f'- teacher reference: `{args.teacher_chosen_json}`',
        '',
        '## Variant Readout',
    ]
    for row in suite_summary:
        summary_lines.append(
            f"- `{row['variant']}`: calib_val exp_delta=`{row['calib_val_exp_delta']:.3f}`, calib_val overhead=`{row['calib_val_overhead']:.6f}`, exp4 exp_delta=`{row['exp4_exp_delta']:.3f}`, exp4 overhead=`{row['exp4_overhead']:.6f}`, hard exp_delta=`{row['hard_exp_delta']:.3f}`, hard overhead=`{row['hard_overhead']:.6f}`"
        )
    best_public = sorted(suite_summary, key=lambda r: (float('-inf') if not np.isfinite(float(r['exp4_exp_delta'])) else float(r['exp4_exp_delta'])), reverse=True)
    summary_lines += ['', '## Ordering']
    for idx, row in enumerate(best_public, start=1):
        summary_lines.append(f"- rank {idx}: `{row['variant']}`")
    (args.reports_root / 'rs_p0cx10_round1_summary.md').write_text('\n'.join(summary_lines), encoding='utf-8')


if __name__ == '__main__':
    main()
