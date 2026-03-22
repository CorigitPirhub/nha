# CX47 Minimal Event Contract V1

- protocol: analysis-only summary of existing `CX46-F` / `CX46-J` public and hard-order evidence; no new branch promoted

## Hard Facts
- `CX46-F` remains the only branch with public negative runtime and real witness activation.
- `CX46-J` improves over `CX46-F` on public, but still does not beat `CX34-A`, and hard order-audit remains positive vs `No-Witness-Transfer`.

## Event Findings
- Positive runtime events are not exhausted by high `witness_hits`; some strong positives have `hits = 0`.
- Therefore `hits`, `family yield`, and `scenario yield` are insufficient as primary event-value signals.
- The dominant discriminative object is not “how many hits happened”, but “whether this review is likely to create a new valuable store”.

## Minimal Event Feature Contract
- Keep `scenario` as a weak prior only; it is not sufficient by itself.
- Keep `class_key` / `must_precede` / `macro-bearing` as structural identifiers.
- Keep `local quality store_strength` as the main instantaneous proxy.
- Keep `event miss streak` as the main online decay variable.
- Keep coarse support count only as a weak bonus, not as the main decision variable.
- Do not use raw `witness_hits` as the primary gating feature.
- Do not use family/scenario/type credit alone as the scheduler target.

## Public Positive Seeds
- `sample_000002.npz` / `narrow_passage`: hits=`623.0`, credit_skips=`17.0`, gain_vs_nowt=`141.093`, gain_vs_nocg=`20.439`
- `sample_000017.npz` / `flange`: hits=`0.0`, credit_skips=`0.0`, gain_vs_nowt=`64.565`, gain_vs_nocg=`56.133`
- `sample_000000.npz` / `parasol_misc`: hits=`271.0`, credit_skips=`0.0`, gain_vs_nowt=`46.706`, gain_vs_nocg=`2.504`
- `sample_000010.npz` / `narrow_passage`: hits=`4.0`, credit_skips=`2016.0`, gain_vs_nowt=`36.226`, gain_vs_nocg=`109.653`
- `sample_000016.npz` / `flange`: hits=`0.0`, credit_skips=`0.0`, gain_vs_nowt=`28.224`, gain_vs_nocg=`4.093`
- `sample_000007.npz` / `parasol_misc`: hits=`5.0`, credit_skips=`500.0`, gain_vs_nowt=`22.051`, gain_vs_nocg=`8.944`
- `sample_000008.npz` / `parasol_misc`: hits=`0.0`, credit_skips=`138.0`, gain_vs_nowt=`15.991`, gain_vs_nocg=`2.892`
- `sample_000005.npz` / `narrow_passage`: hits=`1.0`, credit_skips=`837.0`, gain_vs_nowt=`13.425`, gain_vs_nocg=`13.880`

## Hard Pair Summary
- `alpha_puzzle`: time_delta_ms=`-0.023`, plan_delta_ms=`-0.017`, witness_hits=`0.000`
- `bug_trap`: time_delta_ms=`0.052`, plan_delta_ms=`0.051`, witness_hits=`0.000`
- `deadend_labyrinth`: time_delta_ms=`-0.043`, plan_delta_ms=`-0.041`, witness_hits=`0.000`
- `flange`: time_delta_ms=`-36.608`, plan_delta_ms=`-36.608`, witness_hits=`0.000`
- `maze`: time_delta_ms=`75.521`, plan_delta_ms=`75.518`, witness_hits=`0.000`
- `narrow_passage`: time_delta_ms=`-56.600`, plan_delta_ms=`-56.603`, witness_hits=`312.500`
- `parasol_misc`: time_delta_ms=`-24.575`, plan_delta_ms=`-24.572`, witness_hits=`135.500`

## Next Step
- The next valid branch should predict `review -> store` value directly, using only the minimal contract above, and must avoid expensive extra trace-learning.