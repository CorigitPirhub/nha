from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import pandas as pd


def main() -> None:
    out_root = Path('outputs')
    report_path = Path('reports/rs_p0cx47_event_contract_v1.md')
    report_path.parent.mkdir(parents=True, exist_ok=True)

    f = pd.read_csv(out_root / 'rs_p0cx46_f_rbcc_v1/public_case_rows.csv')
    j = pd.read_csv(out_root / 'rs_p0cx46_j_rrc_public_v1/public_case_rows.csv')
    hard_rows = pd.read_csv(out_root / 'rs_p0cx46_f_hard_order_audit_v1/order_case_rows.csv')

    f_base = f[f.method == 'CX34-A (Full)'][['sample_name', 'scenario', 'time_ms']].rename(columns={'time_ms': 'cx34'})
    f_full = f[f.method == 'CX46-F (Full)'][['sample_name', 'scenario', 'time_ms', 'witness_hits']].rename(columns={'time_ms': 'full', 'witness_hits': 'hits'})
    f_nowt = f[f.method == 'CX46-F (No-Witness-Transfer)'][['sample_name', 'scenario', 'time_ms']].rename(columns={'time_ms': 'nowt'})
    fm = f_base.merge(f_full, on=['sample_name', 'scenario']).merge(f_nowt, on=['sample_name', 'scenario'])
    fm['gain_vs_cx34'] = fm['cx34'] - fm['full']
    fm['gain_vs_nowt'] = fm['nowt'] - fm['full']

    j_base = j[j.method == 'CX34-A (Full)'][['sample_name', 'scenario', 'time_ms']].rename(columns={'time_ms': 'cx34'})
    j_full = j[j.method == 'CX46-J (Full)'][['sample_name', 'scenario', 'time_ms', 'witness_hits', 'credit_gate_skips']].rename(columns={'time_ms': 'full', 'witness_hits': 'hits', 'credit_gate_skips': 'credit_skips'})
    j_nowt = j[j.method == 'CX46-J (No-Witness-Transfer)'][['sample_name', 'scenario', 'time_ms']].rename(columns={'time_ms': 'nowt'})
    j_nocg = j[j.method == 'CX46-J (No-Credit-Gate)'][['sample_name', 'scenario', 'time_ms']].rename(columns={'time_ms': 'nocg'})
    jm = j_base.merge(j_full, on=['sample_name', 'scenario']).merge(j_nowt, on=['sample_name', 'scenario']).merge(j_nocg, on=['sample_name', 'scenario'])
    jm['gain_vs_cx34'] = jm['cx34'] - jm['full']
    jm['gain_vs_nowt'] = jm['nowt'] - jm['full']
    jm['gain_vs_nocg'] = jm['nocg'] - jm['full']

    hard_recs = []
    for (sample, order_name), group in hard_rows.groupby(['sample_name', 'order_name']):
        methods = {method: sub.iloc[0] for method, sub in group.groupby('method')}
        if 'CX46-F (Full)' not in methods or 'CX46-F (No-Witness-Transfer)' not in methods:
            continue
        full = methods['CX46-F (Full)']
        nowt = methods['CX46-F (No-Witness-Transfer)']
        hard_recs.append(
            {
                'sample_name': sample,
                'scenario': full['scenario'],
                'order_name': order_name,
                'time_delta_ms': float(full['time_ms']) - float(nowt['time_ms']),
                'plan_delta_ms': float(full['plan_ms']) - float(nowt['plan_ms']),
                'witness_hits': float(full.get('witness_hits', 0.0)),
            }
        )
    hard_df = pd.DataFrame(hard_recs)

    seeds = []
    for _, row in jm.iterrows():
        label = 'neutral'
        if float(row['gain_vs_nowt']) > 10.0 and float(row['gain_vs_nocg']) > 0.0:
            label = 'positive_event'
        elif float(row['gain_vs_nowt']) < -5.0:
            label = 'negative_event'
        seeds.append(
            {
                'sample_name': row['sample_name'],
                'scenario': row['scenario'],
                'hits': float(row['hits']),
                'credit_skips': float(row['credit_skips']),
                'gain_vs_nowt': float(row['gain_vs_nowt']),
                'gain_vs_nocg': float(row['gain_vs_nocg']),
                'label': label,
            }
        )
    seed_df = pd.DataFrame(seeds)

    lines = [
        '# CX47 Minimal Event Contract V1',
        '',
        '- protocol: analysis-only summary of existing `CX46-F` / `CX46-J` public and hard-order evidence; no new branch promoted',
        '',
        '## Hard Facts',
        '- `CX46-F` remains the only branch with public negative runtime and real witness activation.',
        '- `CX46-J` improves over `CX46-F` on public, but still does not beat `CX34-A`, and hard order-audit remains positive vs `No-Witness-Transfer`.',
        '',
        '## Event Findings',
        '- Positive runtime events are not exhausted by high `witness_hits`; some strong positives have `hits = 0`.',
        '- Therefore `hits`, `family yield`, and `scenario yield` are insufficient as primary event-value signals.',
        '- The dominant discriminative object is not “how many hits happened”, but “whether this review is likely to create a new valuable store”.',
        '',
        '## Minimal Event Feature Contract',
        '- Keep `scenario` as a weak prior only; it is not sufficient by itself.',
        '- Keep `class_key` / `must_precede` / `macro-bearing` as structural identifiers.',
        '- Keep `local quality store_strength` as the main instantaneous proxy.',
        '- Keep `event miss streak` as the main online decay variable.',
        '- Keep coarse support count only as a weak bonus, not as the main decision variable.',
        '- Do not use raw `witness_hits` as the primary gating feature.',
        '- Do not use family/scenario/type credit alone as the scheduler target.',
        '',
        '## Public Positive Seeds',
    ]
    positive = seed_df[seed_df['label'] == 'positive_event'].sort_values('gain_vs_nowt', ascending=False)
    for _, row in positive.iterrows():
        lines.append(
            f"- `{row['sample_name']}` / `{row['scenario']}`: hits=`{row['hits']:.1f}`, credit_skips=`{row['credit_skips']:.1f}`, "
            f"gain_vs_nowt=`{row['gain_vs_nowt']:.3f}`, gain_vs_nocg=`{row['gain_vs_nocg']:.3f}`"
        )
    lines += ['', '## Hard Pair Summary']
    hard_mean = hard_df.groupby('scenario')[['time_delta_ms', 'plan_delta_ms', 'witness_hits']].mean()
    for scenario, row in hard_mean.iterrows():
        lines.append(
            f"- `{scenario}`: time_delta_ms=`{float(row['time_delta_ms']):.3f}`, plan_delta_ms=`{float(row['plan_delta_ms']):.3f}`, witness_hits=`{float(row['witness_hits']):.3f}`"
        )
    lines += ['', '## Next Step']
    lines.append('- The next valid branch should predict `review -> store` value directly, using only the minimal contract above, and must avoid expensive extra trace-learning.')

    report_path.write_text('\n'.join(lines), encoding='utf-8')
    print(report_path)


if __name__ == '__main__':
    main()
