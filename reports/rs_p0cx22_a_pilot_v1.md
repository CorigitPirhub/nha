# CX22-A Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; hard-test consumed only when the frozen public gate passes
- chosen params: `{'max_depth': 3, 'mode_prob_thr': 0.5, 'allowed_bonus': 0.1, 'discouraged_penalty': 0.06, 'forbidden_penalty': 0.1, 'macro_bonus': 0.08, 'must_precede_bonus': 0.1, 'improve_gain': 0.14, 'max_macros': 3, 'step_stride': 2}`
- output root: `outputs/rs_p0cx22_a_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`-14.286`
- exp_delta=`309.429`
- mean_time_overhead_ratio=`3.448779`

## Calib Family Breakdown
- `flange`: exp_delta=`7680.000`, mean_time_overhead_ratio=`0.344528`
- `maze`: exp_delta=`-1906.000`, mean_time_overhead_ratio=`4.231469`
- `narrow_passage`: exp_delta=`325.500`, mean_time_overhead_ratio=`2.626026`
- `parasol_misc`: exp_delta=`-447.000`, mean_time_overhead_ratio=`5.850465`

## Public Parasol vs `CX3-D`
- `exp4` / `CX22-A (Full)`: success_delta_pp=`0.000`, exp_delta=`333.778`, mean_time_overhead_ratio=`3.230091`
- `exp4` / `CX22-A (No-Tree)`: success_delta_pp=`0.000`, exp_delta=`351.722`, mean_time_overhead_ratio=`3.221541`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.028351`

## Public `exp4` Family Breakdown
- `alpha_puzzle` / `CX22-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`3.565214`
- `alpha_puzzle` / `CX22-A (No-Tree)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`3.566761`
- `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.050884`
- `bug_trap` / `CX22-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`3.448479`
- `bug_trap` / `CX22-A (No-Tree)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`3.457680`
- `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.219008`
- `flange` / `CX22-A (Full)`: success_delta_pp=`0.000`, exp_delta=`1484.000`, mean_time_overhead_ratio=`2.929199`
- `flange` / `CX22-A (No-Tree)`: success_delta_pp=`0.000`, exp_delta=`1482.600`, mean_time_overhead_ratio=`2.943795`
- `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.002614`
- `maze` / `CX22-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-117.000`, mean_time_overhead_ratio=`7.216601`
- `maze` / `CX22-A (No-Tree)`: success_delta_pp=`0.000`, exp_delta=`-117.000`, mean_time_overhead_ratio=`7.213308`
- `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.030750`
- `narrow_passage` / `CX22-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-106.500`, mean_time_overhead_ratio=`3.622681`
- `narrow_passage` / `CX22-A (No-Tree)`: success_delta_pp=`0.000`, exp_delta=`-99.750`, mean_time_overhead_ratio=`3.614759`
- `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.006491`
- `parasol_misc` / `CX22-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-144.833`, mean_time_overhead_ratio=`5.050607`
- `parasol_misc` / `CX22-A (No-Tree)`: success_delta_pp=`0.000`, exp_delta=`-94.333`, mean_time_overhead_ratio=`4.595198`
- `parasol_misc` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-451.500`, mean_time_overhead_ratio=`0.950310`

## Hard Benchmark vs `CX3-D`
- skipped: this round keeps hard-test for `CX22-C/D` only; `CX22-A/B` stay public-first.

## Hard Family Breakdown
- skipped: this round keeps hard-test for `CX22-C/D` only; `CX22-A/B` stay public-first.

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`