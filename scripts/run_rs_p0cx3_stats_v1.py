from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Bootstrap stats for accepted P0-CX3 evidence.')
    p.add_argument('--main-variant', type=str, default='cx3_d')
    p.add_argument('--aux-variant', type=str, default='cx3_c')
    p.add_argument('--ablation-root', type=Path, default=Path('outputs/rs_p0cx3_ablation_v1'))
    p.add_argument('--main-root', type=Path, default=Path('outputs/rs_p0cx3_main_trials_v1'))
    p.add_argument('--bootstrap-n', type=int, default=50000)
    p.add_argument('--out-root', type=Path, default=Path('outputs/rs_p0cx3_stats_v1'))
    p.add_argument('--reports-root', type=Path, default=Path('reports'))
    return p.parse_args()


def _bootstrap(arr: np.ndarray, n_boot: int) -> dict[str, float]:
    arr = np.asarray(arr, dtype=np.float64)
    if arr.size == 0:
        return {'mean': float('nan'), 'ci95_lo': float('nan'), 'ci95_hi': float('nan'), 'p_boot_le0': float('nan')}
    rng = np.random.default_rng(20260308)
    boots = np.empty(int(n_boot), dtype=np.float64)
    n = int(arr.size)
    for i in range(int(n_boot)):
        idx = rng.integers(0, n, size=n)
        boots[i] = float(np.mean(arr[idx]))
    return {
        'mean': float(np.mean(arr)),
        'ci95_lo': float(np.quantile(boots, 0.025)),
        'ci95_hi': float(np.quantile(boots, 0.975)),
        'p_boot_le0': float(np.mean(boots <= 0.0)),
    }


def _load_rows(path: Path) -> list[dict[str, str]]:
    with path.open('r', newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _paired_case_map(rows: list[dict[str, str]], budget: str) -> dict[str, dict[str, dict[str, str]]]:
    by: dict[str, dict[str, dict[str, str]]] = {}
    for r in rows:
        if r['budget'] != budget:
            continue
        by.setdefault(r['sample_name'], {})[r['method']] = r
    return by


def _scenario_list(rows: list[dict[str, str]], budget: str) -> list[str]:
    return sorted({r['scenario'] for r in rows if r['budget'] == budget})


def main() -> None:
    args = parse_args()
    args.out_root.mkdir(parents=True, exist_ok=True)
    args.reports_root.mkdir(parents=True, exist_ok=True)

    main_rows = _load_rows(args.ablation_root / args.main_variant / 'case_rows.csv')
    aux_rows = _load_rows(args.ablation_root / args.aux_variant / 'case_rows.csv')
    main_summary = json.loads((args.main_root / args.main_variant / 'chosen.json').read_text(encoding='utf-8'))

    stats_payload: dict[str, Any] = {'main_variant': args.main_variant.upper().replace('_', '-'), 'aux_variant': args.aux_variant.upper().replace('_', '-'), 'budgets': {}}
    report = [
        '# P0-CX3 Statistical Reinforcement',
        '',
        f'- main variant: `{args.main_variant}`',
        f'- auxiliary reference: `{args.aux_variant}`',
        f'- bootstrap_n: `{args.bootstrap_n}`',
        '',
    ]

    for budget in ['exp3', 'exp4']:
        by_main = _paired_case_map(main_rows, budget)
        by_aux = _paired_case_map(aux_rows, budget)
        exp_delta = []
        time_delta = []
        succ_delta = []
        for sample_name, methods in by_main.items():
            if 'Plain-Residual' not in methods or args.main_variant.upper().replace('_', '-') not in methods:
                continue
            plain = methods['Plain-Residual']
            main = methods[args.main_variant.upper().replace('_', '-')]
            exp_delta.append(float(plain['expansions']) - float(main['expansions']))
            time_delta.append(float(plain['time_ms']) - float(main['time_ms']))
            succ_delta.append(float(main['success']) - float(plain['success']))
        budget_stats = {
            'overall_exp_delta_vs_plain': _bootstrap(np.asarray(exp_delta), args.bootstrap_n),
            'overall_time_delta_vs_plain': _bootstrap(np.asarray(time_delta), args.bootstrap_n),
            'overall_success_delta_vs_plain': _bootstrap(np.asarray(succ_delta), args.bootstrap_n),
            'by_scenario': {},
            'main_vs_aux_by_scenario': {},
        }
        for scenario in _scenario_list(main_rows, budget):
            exp_delta_s = []
            succ_delta_s = []
            main_vs_aux = []
            for sample_name, methods in by_main.items():
                if sample_name not in by_aux:
                    continue
                if methods[args.main_variant.upper().replace('_', '-')]['scenario'] != scenario:
                    continue
                plain = methods['Plain-Residual']
                main = methods[args.main_variant.upper().replace('_', '-')]
                aux = by_aux[sample_name][args.aux_variant.upper().replace('_', '-')]
                exp_delta_s.append(float(plain['expansions']) - float(main['expansions']))
                succ_delta_s.append(float(main['success']) - float(plain['success']))
                main_vs_aux.append(float(aux['expansions']) - float(main['expansions']))
            budget_stats['by_scenario'][scenario] = {
                'exp_delta_vs_plain': _bootstrap(np.asarray(exp_delta_s), args.bootstrap_n),
                'success_delta_vs_plain': _bootstrap(np.asarray(succ_delta_s), args.bootstrap_n),
                'num_cases': len(exp_delta_s),
            }
            budget_stats['main_vs_aux_by_scenario'][scenario] = {
                'exp_delta_aux_minus_main': _bootstrap(np.asarray(main_vs_aux), args.bootstrap_n),
                'num_cases': len(main_vs_aux),
            }
        stats_payload['budgets'][budget] = budget_stats

        report.extend([
            f'## {budget.upper()}',
            f"- overall exp delta vs plain: `{budget_stats['overall_exp_delta_vs_plain']}`",
            f"- overall time delta vs plain: `{budget_stats['overall_time_delta_vs_plain']}`",
            f"- overall success delta vs plain: `{budget_stats['overall_success_delta_vs_plain']}`",
        ])
        for scenario in ['parasol_misc', 'narrow_passage', 'flange']:
            if scenario in budget_stats['by_scenario']:
                report.append(f"- {scenario} exp delta vs plain: `{budget_stats['by_scenario'][scenario]['exp_delta_vs_plain']}`")
        report.append('')

    std = main_summary['standard_eval']
    report.extend([
        '## Ordinary Support',
        f"- mp: `{std['mp']}`",
        f"- csm: `{std['csm']}`",
        '',
        '## Reading',
        '- A positive branch is only considered statistically reinforced if the paired expansion delta CI is mostly above zero or the bootstrap mass below zero is small.',
        '- Subgroup evidence matters more than overall mean if the goal is specifically to protect `parasol_misc` while keeping hard-family gains.',
    ])

    (args.out_root / 'stats.json').write_text(json.dumps(stats_payload, indent=2, ensure_ascii=False), encoding='utf-8')
    (args.reports_root / 'rs_p0cx3_stats_v1.md').write_text('\n'.join(report), encoding='utf-8')
    print(f'[rs-p0cx3-stats] report={args.reports_root / "rs_p0cx3_stats_v1.md"}')


if __name__ == '__main__':
    main()
