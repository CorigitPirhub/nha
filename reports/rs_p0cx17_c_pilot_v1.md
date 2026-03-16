# CX17-C Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow` evaluation; hard-test is consumed when public overall turns positive and `flange` stays non-negative
- chosen params: `{'viability_gate': 0.18, 'oracle_gain_thr': 0.03, 'support_slack': 0.16, 'max_macros': 2, 'max_edges': 2, 'macro_bonus': 0.08, 'motif_bonus': 0.08, 'border_bonus': 0.1, 'review_gain': 0.18, 'clearance_w': 0.22, 'corridor_w': 0.24, 'trap_w': 0.32, 'reverse_w': 0.22, 'lateral_w': 0.1, 'forward_w': 0.06, 'heading_w': 0.08, 'stride_cells': 2, 'yaw_stride': 2, 'horizon_steps': 4}`
- output root: `outputs/rs_p0cx17_c_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`0.000`
- exp_delta=`-225.429`
- mean_time_overhead_ratio=`0.645330`

## Calib Family Breakdown
- `flange`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.644507`
- `maze`: exp_delta=`-541.000`, mean_time_overhead_ratio=`0.635856`
- `narrow_passage`: exp_delta=`22.500`, mean_time_overhead_ratio=`0.629603`
- `parasol_misc`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.706030`

## Public Parasol vs `CX3-D`
- `exp3` / `CX17-C (Full)`: success_delta_pp=`0.000`, exp_delta=`3.278`, mean_time_overhead_ratio=`0.689285`
- `exp3` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`0.042909`
- `exp4` / `CX17-C (Full)`: success_delta_pp=`0.000`, exp_delta=`3.278`, mean_time_overhead_ratio=`0.686728`
- `exp4` / `CX17-C (No-Substrate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.112821`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.028351`

## Public `exp4` Family Breakdown
- `alpha_puzzle` / `CX17-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.720298`
- `alpha_puzzle` / `CX17-C (No-Substrate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.078427`
- `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.050884`
- `bug_trap` / `CX17-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.657976`
- `bug_trap` / `CX17-C (No-Substrate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.097158`
- `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.219008`
- `flange` / `CX17-C (Full)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`0.686179`
- `flange` / `CX17-C (No-Substrate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.111344`
- `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.002614`
- `maze` / `CX17-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.664677`
- `maze` / `CX17-C (No-Substrate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.108055`
- `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.030750`
- `narrow_passage` / `CX17-C (Full)`: success_delta_pp=`0.000`, exp_delta=`20.500`, mean_time_overhead_ratio=`0.683722`
- `narrow_passage` / `CX17-C (No-Substrate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.116519`
- `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.006491`
- `parasol_misc` / `CX17-C (Full)`: success_delta_pp=`0.000`, exp_delta=`-4.667`, mean_time_overhead_ratio=`0.726514`
- `parasol_misc` / `CX17-C (No-Substrate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.106528`
- `parasol_misc` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-451.500`, mean_time_overhead_ratio=`0.950310`

## Hard Benchmark vs `CX3-D`
- `CX17-C (Full)`: success_delta_pp=`0.000`, exp_delta=`-4.904`, mean_time_overhead_ratio=`1.030592`, path_delta=`0.017`
- `Hybrid A* (RS)`: success_delta_pp=`1.370`, exp_delta=`214.973`, mean_time_overhead_ratio=`-0.062391`, path_delta=`-0.626`

## Hard Family Breakdown
- `alpha_puzzle` / `CX17-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.135546`
- `bug_trap` / `CX17-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.105179`
- `deadend_labyrinth` / `CX17-C (Full)`: success_delta_pp=`0.000`, exp_delta=`-40.800`, mean_time_overhead_ratio=`0.987857`
- `flange` / `CX17-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.385`, mean_time_overhead_ratio=`1.193906`
- `maze` / `CX17-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.091`, mean_time_overhead_ratio=`0.770724`
- `narrow_passage` / `CX17-C (Full)`: success_delta_pp=`0.000`, exp_delta=`5.538`, mean_time_overhead_ratio=`0.829474`
- `parasol_misc` / `CX17-C (Full)`: success_delta_pp=`0.000`, exp_delta=`-7.000`, mean_time_overhead_ratio=`1.723975`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`

## Final Readout
- result: public ceiling gate cleared.