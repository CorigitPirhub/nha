# CX21-A Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; this round intentionally stayed public-first and did not consume hard-test evidence
- chosen params: `{'cost_gain': 0.1, 'viability_gain': 0.12, 'oracle_gain': 0.08, 'reverse_align_gain': 0.1, 'escape_gain': 0.08, 'support_gain': 0.06, 'uncertainty_penalty': 0.05, 'support_slack': 0.18, 'forward_viability_thr': 0.34, 'reverse_required_thr': 0.08, 'trap_high_thr': 0.56, 'escape_affinity_low_thr': -0.02, 'hopeless_viability_thr': 0.1, 'stride_cells': 2, 'yaw_stride': 2, 'horizon_steps': 5}`
- output root: `outputs/rs_p0cx21_a_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`-14.286`
- exp_delta=`-833.143`
- mean_time_overhead_ratio=`5.338310`

## Calib Family Breakdown
- `flange`: exp_delta=`2436.000`, mean_time_overhead_ratio=`3.813054`
- `maze`: exp_delta=`-2738.000`, mean_time_overhead_ratio=`5.848269`
- `narrow_passage`: exp_delta=`161.500`, mean_time_overhead_ratio=`4.260197`
- `parasol_misc`: exp_delta=`-377.000`, mean_time_overhead_ratio=`7.489916`

## Public Parasol vs `CX3-D`
- `exp4` / `CX21-A (Full)`: success_delta_pp=`0.000`, exp_delta=`55.611`, mean_time_overhead_ratio=`4.936051`
- `exp4` / `CX21-A (No-Consistency)`: success_delta_pp=`0.000`, exp_delta=`45.167`, mean_time_overhead_ratio=`4.793354`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.028351`

## Public `exp4` Family Breakdown
- `alpha_puzzle` / `CX21-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-1.000`, mean_time_overhead_ratio=`5.268652`
- `alpha_puzzle` / `CX21-A (No-Consistency)`: success_delta_pp=`0.000`, exp_delta=`-1.000`, mean_time_overhead_ratio=`5.077539`
- `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.050884`
- `bug_trap` / `CX21-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`4.699558`
- `bug_trap` / `CX21-A (No-Consistency)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`4.496807`
- `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.219008`
- `flange` / `CX21-A (Full)`: success_delta_pp=`0.000`, exp_delta=`173.800`, mean_time_overhead_ratio=`4.899627`
- `flange` / `CX21-A (No-Consistency)`: success_delta_pp=`0.000`, exp_delta=`173.800`, mean_time_overhead_ratio=`4.738335`
- `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.002614`
- `maze` / `CX21-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`5.047204`
- `maze` / `CX21-A (No-Consistency)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`4.884674`
- `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.030750`
- `narrow_passage` / `CX21-A (Full)`: success_delta_pp=`0.000`, exp_delta=`135.500`, mean_time_overhead_ratio=`4.902977`
- `narrow_passage` / `CX21-A (No-Consistency)`: success_delta_pp=`0.000`, exp_delta=`88.500`, mean_time_overhead_ratio=`4.801374`
- `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.006491`
- `parasol_misc` / `CX21-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-68.167`, mean_time_overhead_ratio=`5.934208`
- `parasol_misc` / `CX21-A (No-Consistency)`: success_delta_pp=`0.000`, exp_delta=`-68.167`, mean_time_overhead_ratio=`5.759393`
- `parasol_misc` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-451.500`, mean_time_overhead_ratio=`0.950310`

## Hard Benchmark vs `CX3-D`
- skipped: this round intentionally stayed public-first / ordinary-support (`--skip-hard`), so no hard-test evidence was consumed.

## Hard Family Breakdown
- skipped: this round intentionally stayed public-first / ordinary-support (`--skip-hard`), so no hard-test evidence was consumed.

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`

## Final Readout
- result: public ceiling gate cleared.
