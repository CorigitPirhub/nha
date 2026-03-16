# CX24-D Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; this round intentionally stayed public-first and did not consume hard-test evidence
- chosen params: `{'commit_margin': 0.04, 'sibling_margin': 0.02, 'max_macros': 3}`
- output root: `outputs/rs_p0cx24_d_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`0.000`
- exp_delta=`34.571`
- mean_time_overhead_ratio=`1.962058`

## Calib Family Breakdown
- `flange`: exp_delta=`1363.000`, mean_time_overhead_ratio=`1.688406`
- `maze`: exp_delta=`-357.667`, mean_time_overhead_ratio=`2.070061`
- `narrow_passage`: exp_delta=`164.500`, mean_time_overhead_ratio=`1.522978`
- `parasol_misc`: exp_delta=`-377.000`, mean_time_overhead_ratio=`2.789856`

## Public Parasol vs `CX3-D`
- `exp4` / `CX24-D (Full)`: success_delta_pp=`0.000`, exp_delta=`61.444`, mean_time_overhead_ratio=`1.728946`
- `exp4` / `CX24-D (No-Certificate)`: success_delta_pp=`0.000`, exp_delta=`392.889`, mean_time_overhead_ratio=`1.409516`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.028351`

## Public `exp4` Family Breakdown
- `alpha_puzzle` / `CX24-D (Full)`: success_delta_pp=`0.000`, exp_delta=`-2.000`, mean_time_overhead_ratio=`2.441613`
- `alpha_puzzle` / `CX24-D (No-Certificate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`2.390415`
- `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.050884`
- `bug_trap` / `CX24-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.731461`
- `bug_trap` / `CX24-D (No-Certificate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.664307`
- `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.219008`
- `flange` / `CX24-D (Full)`: success_delta_pp=`0.000`, exp_delta=`218.000`, mean_time_overhead_ratio=`1.749187`
- `flange` / `CX24-D (No-Certificate)`: success_delta_pp=`0.000`, exp_delta=`1428.400`, mean_time_overhead_ratio=`1.301792`
- `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.002614`
- `maze` / `CX24-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.980769`
- `maze` / `CX24-D (No-Certificate)`: success_delta_pp=`0.000`, exp_delta=`-113.000`, mean_time_overhead_ratio=`3.912918`
- `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.030750`
- `narrow_passage` / `CX24-D (Full)`: success_delta_pp=`0.000`, exp_delta=`104.500`, mean_time_overhead_ratio=`1.630769`
- `narrow_passage` / `CX24-D (No-Certificate)`: success_delta_pp=`0.000`, exp_delta=`98.250`, mean_time_overhead_ratio=`1.533259`
- `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.006491`
- `parasol_misc` / `CX24-D (Full)`: success_delta_pp=`0.000`, exp_delta=`-66.667`, mean_time_overhead_ratio=`2.252538`
- `parasol_misc` / `CX24-D (No-Certificate)`: success_delta_pp=`0.000`, exp_delta=`-58.333`, mean_time_overhead_ratio=`2.159795`
- `parasol_misc` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-451.500`, mean_time_overhead_ratio=`0.950310`

## Hard Benchmark vs `CX3-D`
- skipped: this round intentionally stayed public-first / ordinary-support; no hard-test evidence was consumed.

## Hard Family Breakdown
- skipped: this round intentionally stayed public-first / ordinary-support; no hard-test evidence was consumed.

## Observatory
- diagnostic rows saved to `outputs/rs_p0cx24_d_pilot_v1/diagnostic_rows.csv`; state_counts=`{'candidate': 49580, 'commit': 22062, 'observe': 14269, 'recover': 3415}`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`