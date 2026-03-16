# CX23-A Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; this round intentionally stayed public-first and did not consume hard-test evidence
- chosen params: `{'max_depth': 3, 'min_hits': 4, 'min_gain': 0.01, 'prob_thr': 0.5, 'max_macros': 3}`
- output root: `outputs/rs_p0cx23_a_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`-14.286`
- exp_delta=`510.857`
- mean_time_overhead_ratio=`1.520833`

## Calib Family Breakdown
- `flange`: exp_delta=`7682.000`, mean_time_overhead_ratio=`-0.194619`
- `maze`: exp_delta=`-1842.667`, mean_time_overhead_ratio=`2.131864`
- `narrow_passage`: exp_delta=`773.500`, mean_time_overhead_ratio=`0.885561`
- `parasol_misc`: exp_delta=`-125.000`, mean_time_overhead_ratio=`2.673735`

## Public Parasol vs `CX3-D`
- `exp4` / `CX23-A (Full)`: success_delta_pp=`0.000`, exp_delta=`340.500`, mean_time_overhead_ratio=`1.686486`
- `exp4` / `CX23-A (No-Distill)`: success_delta_pp=`0.000`, exp_delta=`326.333`, mean_time_overhead_ratio=`1.573768`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.028351`

## Public `exp4` Family Breakdown
- `alpha_puzzle` / `CX23-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.774851`
- `alpha_puzzle` / `CX23-A (No-Distill)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.690955`
- `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.050884`
- `bug_trap` / `CX23-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.721550`
- `bug_trap` / `CX23-A (No-Distill)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.695852`
- `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.219008`
- `flange` / `CX23-A (Full)`: success_delta_pp=`0.000`, exp_delta=`1421.400`, mean_time_overhead_ratio=`1.497962`
- `flange` / `CX23-A (No-Distill)`: success_delta_pp=`0.000`, exp_delta=`1424.000`, mean_time_overhead_ratio=`1.395179`
- `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.002614`
- `maze` / `CX23-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-113.000`, mean_time_overhead_ratio=`3.823597`
- `maze` / `CX23-A (No-Distill)`: success_delta_pp=`0.000`, exp_delta=`-113.000`, mean_time_overhead_ratio=`3.747813`
- `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.030750`
- `narrow_passage` / `CX23-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-88.000`, mean_time_overhead_ratio=`1.974451`
- `narrow_passage` / `CX23-A (No-Distill)`: success_delta_pp=`0.000`, exp_delta=`-87.750`, mean_time_overhead_ratio=`1.814789`
- `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.006491`
- `parasol_misc` / `CX23-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-85.500`, mean_time_overhead_ratio=`2.450434`
- `parasol_misc` / `CX23-A (No-Distill)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`2.589054`
- `parasol_misc` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-451.500`, mean_time_overhead_ratio=`0.950310`

## Hard Benchmark vs `CX3-D`
- skipped: this round intentionally stayed public-first / ordinary-support; no hard-test evidence was consumed.

## Hard Family Breakdown
- skipped: this round intentionally stayed public-first / ordinary-support; no hard-test evidence was consumed.

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`