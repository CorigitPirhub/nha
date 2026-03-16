# CX25-A Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; this round intentionally stayed public-first and did not consume hard-test evidence
- chosen params: `{'min_hits': 4, 'risk_thr': 0.3, 'transition_thr': 0.3, 'oscillation_thr': 2, 'commit_margin': 0.04, 'sibling_margin': 0.02, 'max_macros': 3}`
- output root: `outputs/rs_p0cx25_a_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`0.000`
- exp_delta=`-331.571`
- mean_time_overhead_ratio=`2.688910`

## Calib Family Breakdown
- `flange`: exp_delta=`1392.000`, mean_time_overhead_ratio=`1.792734`
- `maze`: exp_delta=`-1202.000`, mean_time_overhead_ratio=`3.357094`
- `narrow_passage`: exp_delta=`135.000`, mean_time_overhead_ratio=`2.029897`
- `parasol_misc`: exp_delta=`-377.000`, mean_time_overhead_ratio=`2.898560`

## Public Parasol vs `CX3-D`
- `exp4` / `CX25-A (Full)`: success_delta_pp=`0.000`, exp_delta=`60.722`, mean_time_overhead_ratio=`2.180158`
- `exp4` / `CX25-A (No-Selective-Soft)`: success_delta_pp=`0.000`, exp_delta=`61.444`, mean_time_overhead_ratio=`1.637653`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.028351`

## Public `exp4` Family Breakdown
- `alpha_puzzle` / `CX25-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-2.000`, mean_time_overhead_ratio=`2.906413`
- `alpha_puzzle` / `CX25-A (No-Selective-Soft)`: success_delta_pp=`0.000`, exp_delta=`-2.000`, mean_time_overhead_ratio=`2.963320`
- `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.050884`
- `bug_trap` / `CX25-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.647872`
- `bug_trap` / `CX25-A (No-Selective-Soft)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.637756`
- `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.219008`
- `flange` / `CX25-A (Full)`: success_delta_pp=`0.000`, exp_delta=`224.800`, mean_time_overhead_ratio=`2.290158`
- `flange` / `CX25-A (No-Selective-Soft)`: success_delta_pp=`0.000`, exp_delta=`218.000`, mean_time_overhead_ratio=`1.661083`
- `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.002614`
- `maze` / `CX25-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.947863`
- `maze` / `CX25-A (No-Selective-Soft)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.946283`
- `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.030750`
- `narrow_passage` / `CX25-A (Full)`: success_delta_pp=`0.000`, exp_delta=`92.750`, mean_time_overhead_ratio=`1.960753`
- `narrow_passage` / `CX25-A (No-Selective-Soft)`: success_delta_pp=`0.000`, exp_delta=`104.500`, mean_time_overhead_ratio=`1.537026`
- `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.006491`
- `parasol_misc` / `CX25-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-66.667`, mean_time_overhead_ratio=`2.164044`
- `parasol_misc` / `CX25-A (No-Selective-Soft)`: success_delta_pp=`0.000`, exp_delta=`-66.667`, mean_time_overhead_ratio=`2.117287`
- `parasol_misc` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-451.500`, mean_time_overhead_ratio=`0.950310`

## Hard Benchmark vs `CX3-D`
- skipped: this round intentionally stayed public-first / ordinary-support; no hard-test evidence was consumed.

## Hard Family Breakdown
- skipped: this round intentionally stayed public-first / ordinary-support; no hard-test evidence was consumed.

## Observatory
- diagnostic rows saved to `outputs/rs_p0cx25_a_pilot_v1/diagnostic_rows.csv`; state_counts=`{'candidate': 34104, 'commit': 35531, 'observe': 14453, 'recover': 5251}`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`