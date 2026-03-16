# CX23-D Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; this round intentionally stayed public-first and did not consume hard-test evidence
- chosen params: `{'min_hits': 3, 'min_gain_delta': 0.05, 'max_macros': 3}`
- output root: `outputs/rs_p0cx23_d_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`-14.286`
- exp_delta=`471.571`
- mean_time_overhead_ratio=`1.506056`

## Calib Family Breakdown
- `flange`: exp_delta=`7682.000`, mean_time_overhead_ratio=`-0.220840`
- `maze`: exp_delta=`-1839.667`, mean_time_overhead_ratio=`2.023488`
- `narrow_passage`: exp_delta=`766.000`, mean_time_overhead_ratio=`0.802755`
- `parasol_misc`: exp_delta=`-394.000`, mean_time_overhead_ratio=`3.087257`

## Public Parasol vs `CX3-D`
- `exp4` / `CX23-D (Full)`: success_delta_pp=`0.000`, exp_delta=`326.333`, mean_time_overhead_ratio=`1.544657`
- `exp4` / `CX23-D (No-Editor)`: success_delta_pp=`0.000`, exp_delta=`326.333`, mean_time_overhead_ratio=`1.538882`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.028351`

## Public `exp4` Family Breakdown
- `alpha_puzzle` / `CX23-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.664043`
- `alpha_puzzle` / `CX23-D (No-Editor)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.681070`
- `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.050884`
- `bug_trap` / `CX23-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.629315`
- `bug_trap` / `CX23-D (No-Editor)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.615107`
- `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.219008`
- `flange` / `CX23-D (Full)`: success_delta_pp=`0.000`, exp_delta=`1424.000`, mean_time_overhead_ratio=`1.370474`
- `flange` / `CX23-D (No-Editor)`: success_delta_pp=`0.000`, exp_delta=`1424.000`, mean_time_overhead_ratio=`1.362745`
- `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.002614`
- `maze` / `CX23-D (Full)`: success_delta_pp=`0.000`, exp_delta=`-113.000`, mean_time_overhead_ratio=`3.667787`
- `maze` / `CX23-D (No-Editor)`: success_delta_pp=`0.000`, exp_delta=`-113.000`, mean_time_overhead_ratio=`3.676934`
- `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.030750`
- `narrow_passage` / `CX23-D (Full)`: success_delta_pp=`0.000`, exp_delta=`-87.750`, mean_time_overhead_ratio=`1.779300`
- `narrow_passage` / `CX23-D (No-Editor)`: success_delta_pp=`0.000`, exp_delta=`-87.750`, mean_time_overhead_ratio=`1.780029`
- `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.006491`
- `parasol_misc` / `CX23-D (Full)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`2.538869`
- `parasol_misc` / `CX23-D (No-Editor)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`2.508105`
- `parasol_misc` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-451.500`, mean_time_overhead_ratio=`0.950310`

## Hard Benchmark vs `CX3-D`
- skipped: this round intentionally stayed public-first / ordinary-support; no hard-test evidence was consumed.

## Hard Family Breakdown
- skipped: this round intentionally stayed public-first / ordinary-support; no hard-test evidence was consumed.

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`