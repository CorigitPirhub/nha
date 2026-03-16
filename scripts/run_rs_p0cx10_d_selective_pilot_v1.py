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
from rs_cx10 import cx10_d_las, cx10_d_selective
from rs_cx10.common import load_teacher_memory
from rs_cx8.common import load_nonholonomic_assets, load_nonholonomic_contexts, write_inputs_sha256
from rs_cx4.common import accepted_cx3d_standard


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Run CX10-D-Selective pilot.')
    p.add_argument('--split-root', type=Path, default=Path('data/split/calib_hard_v1'))
    p.add_argument('--parasol-root', type=Path, default=Path('data/benchmark/parasol_narrow/test'))
    p.add_argument('--guard-dev-root', type=Path, default=Path('data/benchmark/rs_root_hard_v2/dev'))
    p.add_argument('--benchmark-root', type=Path, default=Path('data/benchmark'))
    p.add_argument('--ours-checkpoint', type=Path, default=Path('outputs/checkpoints/exp3_final_manual_v11b.pt'))
    p.add_argument('--teacher-chosen-json', type=Path, default=Path('outputs/rs_p0cx8_d_hard_pilot_v1/chosen.json'))
    p.add_argument('--base-chosen-json', type=Path, default=Path('outputs/rs_p0cx10_d_pilot_v1/chosen.json'))
    p.add_argument('--base-out-root', type=Path, default=Path('outputs/rs_p0cx10_d_pilot_v1'))
    p.add_argument('--device', type=str, default='cuda')
    p.add_argument('--dev-cap', type=int, default=20000)
    p.add_argument('--max-mp-cases', type=int, default=800)
    p.add_argument('--max-csm-cases', type=int, default=400)
    p.add_argument('--out-root', type=Path, default=Path('outputs/rs_p0cx10_d_selective_pilot_v1'))
    p.add_argument('--report-path', type=Path, default=Path('reports/rs_p0cx10_d_selective_pilot_v1.md'))
    return p.parse_args()


def _read_split_csv(path: Path) -> list[Path]:
    with path.open('r', newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    return [Path(row['path']) for row in rows]


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
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _method_map(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    return {(str(r['dataset']), str(r['sample_name']), str(r['method'])) if 'dataset' in r else (str(r['sample_name']), str(r['method'])): r for r in rows}


def _path_delta(base_path: float, alt_path: float) -> float:
    if not np.isfinite(float(base_path)) or not np.isfinite(float(alt_path)):
        return float('nan')
    return float(base_path) - float(alt_path)


def _combine_case_rows_from_val(full_rows: list[dict[str, Any]], decisions: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in full_rows:
        sample = str(row['sample_name'])
        dec = decisions[sample]
        if bool(dec['apply_sketch']):
            cx_success = float(row['cx_success'])
            cx_exp = float(row['cx_expansions'])
            cx_time = float(row['cx_time_ms'])
            cx_path = float(row['cx_path_length']) if row['cx_path_length'] not in {'', 'nan', 'NaN'} else float('nan')
            prep_time = float(row['prep_time_ms'])
        else:
            cx_success = float(row['baseline_success'])
            cx_exp = float(row['baseline_expansions'])
            cx_time = float(row['baseline_time_ms'])
            cx_path = float(row['baseline_path_length']) if row['baseline_path_length'] not in {'', 'nan', 'NaN'} else float('nan')
            prep_time = 0.0
        base_success = float(row['baseline_success'])
        base_exp = float(row['baseline_expansions'])
        base_time = float(row['baseline_time_ms'])
        base_path = float(row['baseline_path_length']) if row['baseline_path_length'] not in {'', 'nan', 'NaN'} else float('nan')
        out.append({
            'sample_name': sample,
            'scenario': str(row['scenario']),
            'baseline_success': base_success,
            'baseline_expansions': base_exp,
            'baseline_time_ms': base_time,
            'baseline_path_length': base_path,
            'cx_success': cx_success,
            'cx_expansions': cx_exp,
            'cx_time_ms': cx_time,
            'cx_path_length': cx_path,
            'prep_time_ms': prep_time,
            'apply_sketch': int(bool(dec['apply_sketch'])),
            'guard_probability': float(dec['guard_probability']),
            'sketch_confidence': float(dec['sketch_confidence']),
            'guard_reason': str(dec['guard_reason']),
            'success_delta': cx_success - base_success,
            'exp_delta': base_exp - cx_exp,
            'time_delta_ms': base_time - cx_time,
            'time_overhead_ratio': (cx_time - base_time) / max(base_time, 1e-6),
            'path_delta': _path_delta(base_path, cx_path),
        })
    return out


def _combine_case_rows_from_public(base_public_rows: list[dict[str, Any]], decisions: dict[tuple[str, str], dict[str, Any]]) -> list[dict[str, Any]]:
    idx = {}
    for row in base_public_rows:
        idx[(str(row['dataset']), str(row['sample_name']), str(row['method']))] = row
    out = []
    sample_keys = sorted({(str(r['dataset']), str(r['sample_name'])) for r in base_public_rows})
    for dataset, sample in sample_keys:
        base = idx[(dataset, sample, 'CX3-D')]
        full = idx[(dataset, sample, 'CX10-D (Full)')]
        rs = idx[(dataset, sample, 'Hybrid A* (RS)')]
        out.append({**rs, 'apply_sketch': 0, 'guard_probability': 0.0, 'sketch_confidence': 0.0, 'guard_reason': 'reference'})
        dec = decisions[(dataset, sample)]
        selected = full if bool(dec['apply_sketch']) else base
        out.append({
            'dataset': dataset,
            'sample_name': sample,
            'scenario': str(base['scenario']),
            'method': 'CX10-D-Selective',
            'success': float(selected['success']),
            'expansions': float(selected['expansions']),
            'time_ms': float(selected['time_ms']),
            'prep_time_ms': float(selected.get('prep_time_ms', 0.0 if not bool(dec['apply_sketch']) else selected.get('prep_time_ms', 0.0))),
            'path_length': float(selected['path_length']) if str(selected['path_length']).lower() != 'nan' else float('nan'),
            'apply_sketch': int(bool(dec['apply_sketch'])),
            'guard_probability': float(dec['guard_probability']),
            'sketch_confidence': float(dec['sketch_confidence']),
            'guard_reason': str(dec['guard_reason']),
        })
        out.append({**base, 'apply_sketch': 0, 'guard_probability': 0.0, 'sketch_confidence': 0.0, 'guard_reason': 'baseline'})
        out.append({**full, 'apply_sketch': 1, 'guard_probability': float(dec['guard_probability']), 'sketch_confidence': float(dec['sketch_confidence']), 'guard_reason': 'full_reference'})
    return out


def _summary(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    by = defaultdict(list)
    for row in rows:
        by[tuple(row[k] for k in keys)].append(row)
    out = []
    for key, grp in sorted(by.items()):
        item = {k: key[i] for i, k in enumerate(keys)}
        item.update({
            'num_cases': int(len(grp)),
            'success_rate': float(np.mean([float(r['success']) for r in grp])) if 'success' in grp[0] else float(np.mean([float(r['cx_success']) for r in grp])),
            'avg_expansions': float(np.mean([float(r['expansions']) for r in grp])) if 'expansions' in grp[0] else float(np.mean([float(r['cx_expansions']) for r in grp])),
            'avg_time_ms': float(np.mean([float(r['time_ms']) for r in grp])) if 'time_ms' in grp[0] else float(np.mean([float(r['cx_time_ms']) for r in grp])),
            'avg_path_length': float(np.nanmean([float(r['path_length']) for r in grp])) if 'path_length' in grp[0] else float(np.nanmean([float(r['cx_path_length']) for r in grp])),
            'apply_rate': float(np.mean([float(r.get('apply_sketch', 0.0)) for r in grp])) if grp else 0.0,
        })
        out.append(item)
    return out


def _delta(summary_rows: list[dict[str, Any]], group_keys: tuple[str, ...], baseline_method: str) -> list[dict[str, Any]]:
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
                'apply_rate': float(row.get('apply_rate', 0.0)),
            })
            out.append(item)
    return out


def _classification_metrics(rows: list[dict[str, Any]], prob_thr: float, conf_thr: float) -> dict[str, Any]:
    tp = fp = tn = fn = 0
    applied = 0
    for row in rows:
        apply = float(row['guard_probability']) >= float(prob_thr) and float(row['sketch_confidence']) >= float(conf_thr)
        y = int(row['label'])
        applied += int(apply)
        if apply and y == 1:
            tp += 1
        elif apply and y == 0:
            fp += 1
        elif (not apply) and y == 0:
            tn += 1
        else:
            fn += 1
    return {'tp': tp, 'fp': fp, 'tn': tn, 'fn': fn, 'applied': applied}


def _decision_from_prob(row: dict[str, Any], params: cx10_d_selective.CX10DSelectiveParams) -> dict[str, Any]:
    apply = float(row['guard_probability']) >= float(params.prob_threshold) and float(row['sketch_confidence']) >= float(params.sketch_conf_threshold)
    reason = 'safe' if apply else ('low_prob' if float(row['guard_probability']) < float(params.prob_threshold) else 'low_conf')
    return {
        'apply_sketch': bool(apply),
        'guard_probability': float(row['guard_probability']),
        'sketch_confidence': float(row['sketch_confidence']),
        'guard_reason': reason,
    }


def _standard_audit(predictor, max_mp_cases: int, max_csm_cases: int) -> list[dict[str, Any]]:
    rows = []
    for dataset, limit in [('mp', int(max_mp_cases)), ('csm', int(max_csm_cases))]:
        files = sorted((Path('data/benchmark') / dataset / 'test').glob('sample_*.npz'))[:limit]
        diffs = []
        for idx, path in enumerate(files, start=1):
            sample = load_grid_sample(path)
            _, accepted = accepted_cx3d_standard(sample, predictor)
            field = cx10_d_selective.build_standard_field(sample, predictor, None, None)
            diffs.append(float(np.max(np.abs(np.asarray(field, dtype=np.float32) - np.asarray(accepted, dtype=np.float32)))))
            if idx % 100 == 0 or idx == len(files):
                print(f'[standard-audit:{dataset}] {idx}/{len(files)}')
        rows.append({
            'dataset': dataset,
            'num_cases': int(len(files)),
            'max_abs_field_diff': float(max(diffs) if diffs else 0.0),
            'mean_abs_field_diff': float(np.mean(diffs) if diffs else 0.0),
        })
    return rows


def main() -> None:
    args = parse_args()
    args.out_root.mkdir(parents=True, exist_ok=True)
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    predictor = NeuralHeuristicPredictor(args.ours_checkpoint, device=args.device, gaussian_sigma=2.5)
    cfg = CXGlobalConfig()
    teacher_memory = load_teacher_memory(args.teacher_chosen_json, args.device)
    teacher_memory['device'] = str(args.device)
    base_chosen = json.loads(args.base_chosen_json.read_text(encoding='utf-8'))
    base_params = cx10_d_las.CX10DLASParams(**base_chosen['params'])

    train_files = _read_split_csv(args.split_root / 'calib_train.csv')
    val_files = _read_split_csv(args.split_root / 'calib_val.csv')
    train_assets = load_nonholonomic_assets(train_files, predictor, cfg, int(args.dev_cap), tag='cx10d-selective:train')
    val_assets = load_nonholonomic_assets(val_files, predictor, cfg, int(args.dev_cap), tag='cx10d-selective:val')
    guard_train_files = sorted(args.guard_dev_root.glob('sample_*.npz'))
    guard_train_assets = load_nonholonomic_contexts(guard_train_files, predictor, cfg, tag='cx10d-selective:guard-dev')
    public_files = sorted(args.parasol_root.glob('sample_*.npz'))
    public_assets = load_nonholonomic_contexts(public_files, predictor, cfg, tag='cx10d-selective:public')

    base_memory = cx10_d_las.fit_variant(
        train_assets,
        val_assets,
        predictor,
        cfg,
        base_params,
        args.out_root / 'base_refit',
        args.device,
        dependencies={'teacher_memory': teacher_memory, 'teacher_chosen_json': args.teacher_chosen_json},
    )

    trial_rows = []
    val_case_features = []
    public_case_features = []

    selective_rows_cache = {}
    calib_full_rows = _read_csv(args.base_out_root / 'calib_val_case_rows.csv')
    public_full_rows = _read_csv(args.base_out_root / 'public_case_rows.csv')

    for params in cx10_d_selective.param_grid():
        memory = cx10_d_selective.fit_variant(guard_train_assets, val_assets, predictor, cfg, params, args.out_root / f"guard_prob_{str(params.prob_threshold).replace('.', 'p')}_conf_{str(params.sketch_conf_threshold).replace('.', 'p')}", args.device, dependencies={'base_memory': base_memory, 'base_params': base_params})
        val_rows = []
        for asset in val_assets:
            decision, feature, meta, _ = cx10_d_selective.guard_decision(memory, params, base_memory, base_params, asset['case'], asset['bundle'], asset['field'], args.device)
            val_rows.append({
                'sample_name': str(asset['path'].name),
                'scenario': str(asset['case']['scenario']),
                'label': 1 if str(asset['case']['scenario']) == 'narrow_passage' else 0,
                'guard_probability': float(decision.probability),
                'sketch_confidence': float(decision.sketch_confidence),
                'guard_reason': str(decision.reason),
                'feature': feature,
                **meta,
            })
        metrics = _classification_metrics(val_rows, params.prob_threshold, params.sketch_conf_threshold)
        decisions = {str(r['sample_name']): _decision_from_prob(r, params) for r in val_rows}
        selective_case_rows = _combine_case_rows_from_val(calib_full_rows, decisions)
        val_summary = {
            'success_delta_pp': 100.0 * float(np.mean([r['success_delta'] for r in selective_case_rows])) if selective_case_rows else 0.0,
            'exp_delta': float(np.mean([r['exp_delta'] for r in selective_case_rows])) if selective_case_rows else 0.0,
            'time_delta_ms': float(np.mean([r['time_delta_ms'] for r in selective_case_rows])) if selective_case_rows else 0.0,
            'time_overhead_ratio': float(np.mean([r['time_overhead_ratio'] for r in selective_case_rows])) if selective_case_rows else 0.0,
            'path_delta': float(np.nanmean([r['path_delta'] for r in selective_case_rows])) if selective_case_rows else float('nan'),
        }
        trial_rows.append({
            'params': params,
            'memory': memory,
            'val_rows': val_rows,
            'metrics': metrics,
            'val_summary': val_summary,
        })
        print(f'[cx10d-selective] params={params} metrics={metrics} val_summary={val_summary}')
        selective_rows_cache[(params.prob_threshold, params.sketch_conf_threshold)] = selective_case_rows

    trial_rows.sort(key=lambda t: (-(t['metrics']['fp'] == 0), -int(t['metrics']['tp']), int(t['metrics']['fp']), int(t['metrics']['applied'])), reverse=False)
    # explicit selector: prioritize zero false positives, then more true positives, then fewer false positives, then fewer total applies
    trial_rows = sorted(trial_rows, key=lambda t: (
        int(t['metrics']['fp']),
        -int(t['metrics']['tp']),
        int(t['metrics']['applied']),
        -float(t['val_summary']['exp_delta']),
    ))
    chosen = trial_rows[0]
    chosen_params = chosen['params']
    chosen_memory = chosen['memory']

    chosen_val_rows = chosen['val_rows']
    chosen_decisions_val = {str(r['sample_name']): _decision_from_prob(r, chosen_params) for r in chosen_val_rows}
    chosen_selective_val = selective_rows_cache[(chosen_params.prob_threshold, chosen_params.sketch_conf_threshold)]
    _write_csv(args.out_root / 'calib_val_case_rows.csv', chosen_selective_val)

    family_val = []
    by = defaultdict(list)
    for row in chosen_selective_val:
        by[str(row['scenario'])].append(row)
    for scenario, grp in sorted(by.items()):
        family_val.append({
            'scenario': scenario,
            'num_cases': int(len(grp)),
            'success_delta_pp': 100.0 * float(np.mean([r['success_delta'] for r in grp])),
            'exp_delta': float(np.mean([r['exp_delta'] for r in grp])),
            'time_overhead_ratio': float(np.mean([r['time_overhead_ratio'] for r in grp])),
            'apply_rate': float(np.mean([r['apply_sketch'] for r in grp])),
        })
    _write_csv(args.out_root / 'calib_val_family_rows.csv', family_val)

    for asset in public_assets:
        decision, feature, meta, _ = cx10_d_selective.guard_decision(chosen_memory, chosen_params, base_memory, base_params, asset['case'], asset['bundle'], asset['field'], args.device)
        public_case_features.append({
            'dataset': 'exp3',
            'sample_name': str(asset['path'].name),
            'scenario': str(asset['case']['scenario']),
            'label': 1 if str(asset['case']['scenario']) == 'narrow_passage' else 0,
            'guard_probability': float(decision.probability),
            'sketch_confidence': float(decision.sketch_confidence),
            'guard_reason': str(decision.reason),
            **meta,
        })
    public_decisions = {(dataset, sample): _decision_from_prob(row, chosen_params) for row in public_case_features for dataset in ('exp3', 'exp4') for sample in [row['sample_name']]}
    public_case_rows = _combine_case_rows_from_public(public_full_rows, public_decisions)
    _write_csv(args.out_root / 'public_case_rows.csv', public_case_rows)
    public_summary = _summary(public_case_rows, ('dataset', 'method'))
    public_delta = _delta(public_summary, ('dataset',), baseline_method='CX3-D')
    public_family_summary = _summary(public_case_rows, ('dataset', 'scenario', 'method'))
    public_family_delta = _delta(public_family_summary, ('dataset', 'scenario'), baseline_method='CX3-D')
    _write_csv(args.out_root / 'public_summary.csv', public_summary)
    _write_csv(args.out_root / 'public_delta.csv', public_delta)
    _write_csv(args.out_root / 'public_family_delta.csv', public_family_delta)

    standard_audit = _standard_audit(predictor, int(args.max_mp_cases), int(args.max_csm_cases))
    _write_csv(args.out_root / 'standard_field_audit.csv', standard_audit)

    chosen_json = {
        'variant': 'CX10-D-Selective',
        'base_variant': 'CX10-D',
        'base_params': base_chosen['params'],
        'guard_params': vars(chosen_params),
        'classification_metrics_val': chosen['metrics'],
        'val_summary': chosen['val_summary'],
        'base_fit_dir': str(base_chosen['fit_dir']),
        'teacher_chosen_json': str(args.teacher_chosen_json),
    }
    (args.out_root / 'chosen.json').write_text(json.dumps(chosen_json, indent=2, ensure_ascii=False), encoding='utf-8')
    _write_csv(args.out_root / 'guard_val_rows.csv', [{k: v for k, v in r.items() if k != 'feature'} for r in chosen_val_rows])
    _write_csv(args.out_root / 'guard_public_rows.csv', public_case_features)

    inputs = [args.ours_checkpoint, args.teacher_chosen_json, args.base_chosen_json, args.split_root / 'manifest.json', args.split_root / 'calib_train.csv', args.split_root / 'calib_val.csv']
    inputs += train_files + val_files + guard_train_files + public_files
    write_inputs_sha256(inputs, args.out_root / 'inputs_sha256.json')
    manifest = {
        'version': 'rs_p0cx10_d_selective_pilot_v1',
        'runtime_hours': float((time.perf_counter() - t0) / 3600.0),
        'chosen': chosen_json,
        'inputs_sha256': json.loads((args.out_root / 'inputs_sha256.json').read_text(encoding='utf-8')),
    }
    (args.out_root / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')

    delta_map = {(str(r['dataset']), str(r['method'])): r for r in public_delta}
    exp4_sel = delta_map.get(('exp4', 'CX10-D-Selective'))
    exp3_sel = delta_map.get(('exp3', 'CX10-D-Selective'))
    flange_exp4 = next((r for r in public_family_delta if r['dataset'] == 'exp4' and r['scenario'] == 'flange' and r['method'] == 'CX10-D-Selective'), None)
    narrow_exp4 = next((r for r in public_family_delta if r['dataset'] == 'exp4' and r['scenario'] == 'narrow_passage' and r['method'] == 'CX10-D-Selective'), None)

    lines = [
        '# CX10-D-Selective Pilot V1',
        '',
        '- protocol: base sketch params locked from `outputs/rs_p0cx10_d_pilot_v1/chosen.json`; only the family-aware abstention guard is fit on `calib_hard_v1` dev split',
        f"- teacher chosen json: `{args.teacher_chosen_json}`",
        f"- base chosen json: `{args.base_chosen_json}`",
        f"- chosen guard params: `{vars(chosen_params)}`",
        f"- val classification metrics: `{chosen['metrics']}`",
        f"- inputs sha256: `{args.out_root / 'inputs_sha256.json'}`",
        '',
        '## Calib Val vs accepted `CX3-D`',
        f"- success_delta_pp=`{chosen['val_summary']['success_delta_pp']:.3f}`",
        f"- exp_delta=`{chosen['val_summary']['exp_delta']:.3f}`",
        f"- mean_time_overhead_ratio=`{chosen['val_summary']['time_overhead_ratio']:.6f}`",
        f"- path_delta=`{chosen['val_summary']['path_delta']:.3f}`",
        '',
        '## Calib Family Breakdown',
    ]
    for row in family_val:
        lines.append(f"- `{row['scenario']}`: success_delta_pp=`{float(row['success_delta_pp']):.3f}`, exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['time_overhead_ratio']):.6f}`, apply_rate=`{float(row['apply_rate']):.3f}`")
    lines += ['', '## Public Parasol vs `CX3-D`']
    for row in public_delta:
        lines.append(f"- `{row['dataset']}` / `{row['method']}`: success_delta_pp=`{float(row['success_delta_pp']):.3f}`, exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`, apply_rate=`{float(row['apply_rate']):.3f}`")
    lines += ['', '## Public Family Delta vs `CX3-D`']
    for row in public_family_delta:
        if row['method'] in {'CX10-D-Selective', 'CX10-D (Full)'} and row['dataset'] == 'exp4':
            lines.append(f"- `{row['scenario']}` / `{row['method']}`: success_delta_pp=`{float(row['success_delta_pp']):.3f}`, exp_delta=`{float(row['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(row['mean_time_overhead_ratio']):.6f}`, apply_rate=`{float(row['apply_rate']):.3f}`")
    lines += ['', '## Standard Support Audit']
    for row in standard_audit:
        lines.append(f"- `{row['dataset']}`: num_cases=`{row['num_cases']}`, max_abs_field_diff=`{float(row['max_abs_field_diff']):.6f}`, mean_abs_field_diff=`{float(row['mean_abs_field_diff']):.6f}`")
    lines += ['', '## Final Readout']
    if exp4_sel is not None and flange_exp4 is not None and narrow_exp4 is not None:
        lines.append(f"- `exp4` selective overall: exp_delta=`{float(exp4_sel['exp_delta']):.3f}`, mean_time_overhead_ratio=`{float(exp4_sel['mean_time_overhead_ratio']):.6f}`")
        lines.append(f"- `exp4` flange selective: exp_delta=`{float(flange_exp4['exp_delta']):.3f}`")
        lines.append(f"- `exp4` narrow_passage selective: exp_delta=`{float(narrow_exp4['exp_delta']):.3f}`")
        passed = float(exp4_sel['exp_delta']) > 0.0 and float(exp4_sel['mean_time_overhead_ratio']) < 0.30 and float(flange_exp4['exp_delta']) >= 0.0
        if passed:
            lines.append('- result: selective family-aware abstention clears the public gate and rescues CX10-D for the next stage.')
        else:
            lines.append('- result: selective abstention does not fully clear the public gate.')
    args.report_path.write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    main()
