# CX20-B Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow` evaluation; hard-test is consumed when public overall turns positive and `flange` stays non-negative
- chosen params: `{'safe_cost': 12.0, 'boundary_viability': 0.18, 'reverse_required_thr': 0.08, 'oracle_gain_thr': 0.02, 'trap_high_thr': 0.55, 'support_slack': 0.16, 'max_macros': 2, 'grammar_bonus': 0.1, 'macro_bonus': 0.08, 'improve_gain': 0.24, 'stride_cells': 2, 'yaw_stride': 2, 'horizon_steps': 5}`
- output root: `outputs/rs_p0cx20_b_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`-14.286`
- exp_delta=`-833.143`
- mean_time_overhead_ratio=`3.135820`

## Calib Family Breakdown
- `flange`: exp_delta=`2436.000`, mean_time_overhead_ratio=`2.022678`
- `maze`: exp_delta=`-2738.000`, mean_time_overhead_ratio=`3.520141`
- `narrow_passage`: exp_delta=`161.500`, mean_time_overhead_ratio=`2.442510`
- `parasol_misc`: exp_delta=`-377.000`, mean_time_overhead_ratio=`4.482622`

## Public Parasol vs `CX3-D`
- `exp3` / `CX20-B (Full)`: success_delta_pp=`0.000`, exp_delta=`-90.222`, mean_time_overhead_ratio=`3.135466`
- `exp3` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`0.042909`
- `exp4` / `CX20-B (Full)`: success_delta_pp=`0.000`, exp_delta=`45.111`, mean_time_overhead_ratio=`2.956978`
- `exp4` / `CX20-B (No-Grammar)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.403237`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.028351`

## Public `exp4` Family Breakdown
- `alpha_puzzle` / `CX20-B (Full)`: success_delta_pp=`0.000`, exp_delta=`-1.000`, mean_time_overhead_ratio=`3.149485`
- `alpha_puzzle` / `CX20-B (No-Grammar)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.483436`
- `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.050884`
- `bug_trap` / `CX20-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`2.780997`
- `bug_trap` / `CX20-B (No-Grammar)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.404221`
- `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.219008`
- `flange` / `CX20-B (Full)`: success_delta_pp=`0.000`, exp_delta=`173.800`, mean_time_overhead_ratio=`2.929454`
- `flange` / `CX20-B (No-Grammar)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.397558`
- `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.002614`
- `maze` / `CX20-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`2.955447`
- `maze` / `CX20-B (No-Grammar)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.396879`
- `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.030750`
- `narrow_passage` / `CX20-B (Full)`: success_delta_pp=`0.000`, exp_delta=`88.750`, mean_time_overhead_ratio=`2.945107`
- `narrow_passage` / `CX20-B (No-Grammar)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.407739`
- `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.006491`
- `parasol_misc` / `CX20-B (Full)`: success_delta_pp=`0.000`, exp_delta=`-68.500`, mean_time_overhead_ratio=`3.592196`
- `parasol_misc` / `CX20-B (No-Grammar)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.468747`
- `parasol_misc` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-451.500`, mean_time_overhead_ratio=`0.950310`

## Hard Benchmark vs `CX3-D`
- `CX20-B (Full)`: success_delta_pp=`-1.370`, exp_delta=`20.411`, mean_time_overhead_ratio=`3.709393`, path_delta=`1.099`
- `Hybrid A* (RS)`: success_delta_pp=`1.370`, exp_delta=`214.973`, mean_time_overhead_ratio=`-0.062391`, path_delta=`-0.626`

## Hard Family Breakdown
- `alpha_puzzle` / `CX20-B (Full)`: success_delta_pp=`0.000`, exp_delta=`-0.091`, mean_time_overhead_ratio=`3.962748`
- `bug_trap` / `CX20-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`3.883212`
- `deadend_labyrinth` / `CX20-B (Full)`: success_delta_pp=`0.000`, exp_delta=`-147.300`, mean_time_overhead_ratio=`3.612840`
- `flange` / `CX20-B (Full)`: success_delta_pp=`0.000`, exp_delta=`-120.538`, mean_time_overhead_ratio=`4.130330`
- `maze` / `CX20-B (Full)`: success_delta_pp=`-9.091`, exp_delta=`562.818`, mean_time_overhead_ratio=`3.013434`
- `narrow_passage` / `CX20-B (Full)`: success_delta_pp=`0.000`, exp_delta=`-122.846`, mean_time_overhead_ratio=`3.496997`
- `parasol_misc` / `CX20-B (Full)`: success_delta_pp=`0.000`, exp_delta=`-15.750`, mean_time_overhead_ratio=`5.619154`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`

## Final Readout
- result: public ceiling gate cleared.