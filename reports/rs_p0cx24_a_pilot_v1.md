# CX24-A Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; this round intentionally stayed public-first and did not consume hard-test evidence
- chosen params: `{'min_hits': 3, 'support_slack': 0.18, 'trap_sim_margin': 0.0, 'max_macros': 3}`
- output root: `outputs/rs_p0cx24_a_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`-14.286`
- exp_delta=`1218.571`
- mean_time_overhead_ratio=`1.442802`

## Calib Family Breakdown
- `flange`: exp_delta=`7682.000`, mean_time_overhead_ratio=`-0.155796`
- `maze`: exp_delta=`65.667`, mean_time_overhead_ratio=`1.868122`
- `narrow_passage`: exp_delta=`381.000`, mean_time_overhead_ratio=`1.202254`
- `parasol_misc`: exp_delta=`-111.000`, mean_time_overhead_ratio=`2.246536`

## Public Parasol vs `CX3-D`
- `exp4` / `CX24-A (Full)`: success_delta_pp=`0.000`, exp_delta=`392.889`, mean_time_overhead_ratio=`1.528259`
- `exp4` / `CX24-A (No-Trap-Witness)`: success_delta_pp=`0.000`, exp_delta=`392.889`, mean_time_overhead_ratio=`1.421876`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.028351`

## Public `exp4` Family Breakdown
- `alpha_puzzle` / `CX24-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`2.316388`
- `alpha_puzzle` / `CX24-A (No-Trap-Witness)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`2.193713`
- `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.050884`
- `bug_trap` / `CX24-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.757270`
- `bug_trap` / `CX24-A (No-Trap-Witness)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.663306`
- `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.219008`
- `flange` / `CX24-A (Full)`: success_delta_pp=`0.000`, exp_delta=`1428.400`, mean_time_overhead_ratio=`1.408711`
- `flange` / `CX24-A (No-Trap-Witness)`: success_delta_pp=`0.000`, exp_delta=`1428.400`, mean_time_overhead_ratio=`1.310354`
- `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.002614`
- `maze` / `CX24-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-113.000`, mean_time_overhead_ratio=`4.060454`
- `maze` / `CX24-A (No-Trap-Witness)`: success_delta_pp=`0.000`, exp_delta=`-113.000`, mean_time_overhead_ratio=`3.868223`
- `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.030750`
- `narrow_passage` / `CX24-A (Full)`: success_delta_pp=`0.000`, exp_delta=`98.250`, mean_time_overhead_ratio=`1.673625`
- `narrow_passage` / `CX24-A (No-Trap-Witness)`: success_delta_pp=`0.000`, exp_delta=`98.250`, mean_time_overhead_ratio=`1.555003`
- `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.006491`
- `parasol_misc` / `CX24-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-58.333`, mean_time_overhead_ratio=`2.299430`
- `parasol_misc` / `CX24-A (No-Trap-Witness)`: success_delta_pp=`0.000`, exp_delta=`-58.333`, mean_time_overhead_ratio=`2.160088`
- `parasol_misc` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-451.500`, mean_time_overhead_ratio=`0.950310`

## Hard Benchmark vs `CX3-D`
- skipped: this round intentionally stayed public-first / ordinary-support; no hard-test evidence was consumed.

## Hard Family Breakdown
- skipped: this round intentionally stayed public-first / ordinary-support; no hard-test evidence was consumed.

## Observatory
- diagnostic rows saved to `outputs/rs_p0cx24_a_pilot_v1/diagnostic_rows.csv`; state_counts=`{'candidate': 20497, 'commit': 36315, 'recover': 17498, 'observe': 9050}`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`