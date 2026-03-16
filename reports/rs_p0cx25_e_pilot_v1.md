# CX25-E Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; this round intentionally stayed public-first and did not consume hard-test evidence
- chosen params: `{'min_hits': 3, 'worst_group_floor': 0.0, 'tail_floor': 0.0}`
- output root: `outputs/rs_p0cx25_e_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`0.000`
- exp_delta=`34.571`
- mean_time_overhead_ratio=`1.953874`

## Calib Family Breakdown
- `flange`: exp_delta=`1363.000`, mean_time_overhead_ratio=`1.688852`
- `maze`: exp_delta=`-357.667`, mean_time_overhead_ratio=`2.055922`
- `narrow_passage`: exp_delta=`164.500`, mean_time_overhead_ratio=`1.481868`
- `parasol_misc`: exp_delta=`-377.000`, mean_time_overhead_ratio=`2.856765`

## Public Parasol vs `CX3-D`
- `exp4` / `CX25-E (Full)`: success_delta_pp=`0.000`, exp_delta=`61.444`, mean_time_overhead_ratio=`1.734947`
- `exp4` / `CX25-E (No-Group-Stable)`: success_delta_pp=`0.000`, exp_delta=`61.444`, mean_time_overhead_ratio=`1.698736`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.028351`

## Public `exp4` Family Breakdown
- `alpha_puzzle` / `CX25-E (Full)`: success_delta_pp=`0.000`, exp_delta=`-2.000`, mean_time_overhead_ratio=`3.110235`
- `alpha_puzzle` / `CX25-E (No-Group-Stable)`: success_delta_pp=`0.000`, exp_delta=`-2.000`, mean_time_overhead_ratio=`3.132412`
- `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.050884`
- `bug_trap` / `CX25-E (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.756238`
- `bug_trap` / `CX25-E (No-Group-Stable)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.699402`
- `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.219008`
- `flange` / `CX25-E (Full)`: success_delta_pp=`0.000`, exp_delta=`218.000`, mean_time_overhead_ratio=`1.751601`
- `flange` / `CX25-E (No-Group-Stable)`: success_delta_pp=`0.000`, exp_delta=`218.000`, mean_time_overhead_ratio=`1.719910`
- `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.002614`
- `maze` / `CX25-E (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`2.016353`
- `maze` / `CX25-E (No-Group-Stable)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`2.009454`
- `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.030750`
- `narrow_passage` / `CX25-E (Full)`: success_delta_pp=`0.000`, exp_delta=`104.500`, mean_time_overhead_ratio=`1.643320`
- `narrow_passage` / `CX25-E (No-Group-Stable)`: success_delta_pp=`0.000`, exp_delta=`104.500`, mean_time_overhead_ratio=`1.601641`
- `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.006491`
- `parasol_misc` / `CX25-E (Full)`: success_delta_pp=`0.000`, exp_delta=`-66.667`, mean_time_overhead_ratio=`2.259725`
- `parasol_misc` / `CX25-E (No-Group-Stable)`: success_delta_pp=`0.000`, exp_delta=`-66.667`, mean_time_overhead_ratio=`2.187260`
- `parasol_misc` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-451.500`, mean_time_overhead_ratio=`0.950310`

## Hard Benchmark vs `CX3-D`
- skipped: this round intentionally stayed public-first / ordinary-support; no hard-test evidence was consumed.

## Hard Family Breakdown
- skipped: this round intentionally stayed public-first / ordinary-support; no hard-test evidence was consumed.

## Observatory
- diagnostic rows saved to `outputs/rs_p0cx25_e_pilot_v1/diagnostic_rows.csv`; state_counts=`{'candidate': 49580, 'commit': 22062, 'observe': 14269, 'recover': 3415}`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`