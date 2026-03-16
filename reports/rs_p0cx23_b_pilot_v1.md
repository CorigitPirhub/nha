# CX23-B Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; this round intentionally stayed public-first and did not consume hard-test evidence
- chosen params: `{'min_hits': 4, 'suppress_margin': 0.01, 'promote_margin': 0.03, 'support_slack': 0.18, 'max_macros': 3}`
- output root: `outputs/rs_p0cx23_b_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`-14.286`
- exp_delta=`471.571`
- mean_time_overhead_ratio=`1.546203`

## Calib Family Breakdown
- `flange`: exp_delta=`7682.000`, mean_time_overhead_ratio=`-0.209606`
- `maze`: exp_delta=`-1839.667`, mean_time_overhead_ratio=`2.072433`
- `narrow_passage`: exp_delta=`766.000`, mean_time_overhead_ratio=`0.839575`
- `parasol_misc`: exp_delta=`-394.000`, mean_time_overhead_ratio=`3.136573`

## Public Parasol vs `CX3-D`
- `exp4` / `CX23-B (Full)`: success_delta_pp=`0.000`, exp_delta=`326.333`, mean_time_overhead_ratio=`1.580398`
- `exp4` / `CX23-B (No-Contrastive)`: success_delta_pp=`0.000`, exp_delta=`326.333`, mean_time_overhead_ratio=`1.463126`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.028351`

## Public `exp4` Family Breakdown
- `alpha_puzzle` / `CX23-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.705322`
- `alpha_puzzle` / `CX23-B (No-Contrastive)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.570452`
- `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.050884`
- `bug_trap` / `CX23-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.645540`
- `bug_trap` / `CX23-B (No-Contrastive)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.563291`
- `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.219008`
- `flange` / `CX23-B (Full)`: success_delta_pp=`0.000`, exp_delta=`1424.000`, mean_time_overhead_ratio=`1.402440`
- `flange` / `CX23-B (No-Contrastive)`: success_delta_pp=`0.000`, exp_delta=`1424.000`, mean_time_overhead_ratio=`1.289255`
- `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.002614`
- `maze` / `CX23-B (Full)`: success_delta_pp=`0.000`, exp_delta=`-113.000`, mean_time_overhead_ratio=`3.739048`
- `maze` / `CX23-B (No-Contrastive)`: success_delta_pp=`0.000`, exp_delta=`-113.000`, mean_time_overhead_ratio=`3.537613`
- `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.030750`
- `narrow_passage` / `CX23-B (Full)`: success_delta_pp=`0.000`, exp_delta=`-87.750`, mean_time_overhead_ratio=`1.823224`
- `narrow_passage` / `CX23-B (No-Contrastive)`: success_delta_pp=`0.000`, exp_delta=`-87.750`, mean_time_overhead_ratio=`1.702731`
- `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.006491`
- `parasol_misc` / `CX23-B (Full)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`2.567511`
- `parasol_misc` / `CX23-B (No-Contrastive)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`2.407131`
- `parasol_misc` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-451.500`, mean_time_overhead_ratio=`0.950310`

## Hard Benchmark vs `CX3-D`
- skipped: this round intentionally stayed public-first / ordinary-support; no hard-test evidence was consumed.

## Hard Family Breakdown
- skipped: this round intentionally stayed public-first / ordinary-support; no hard-test evidence was consumed.

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`