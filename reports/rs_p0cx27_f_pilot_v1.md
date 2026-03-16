# CX27-F Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; this round stayed public-first and did not consume hard-test evidence
- chosen params: `{'maze_revisit_thr': 2, 'maze_stall_steps': 14, 'misc_revisit_thr': 1, 'misc_churn_thr': 0.2, 'reverse_required_thr': 0.06, 'trap_thr': 0.48, 'progress_eps': 0.02, 'commit_fail_margin': 0.04, 'failure_ttl': 28, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24}`
- output root: `outputs/rs_p0cx27_f_pilot_v1`

## Public vs `CX3-D`
- `CX27-F (Full)`: success_delta_pp=`0.000`, exp_delta=`395.833`, mean_time_overhead_ratio=`2.400491`
- `CX27-F (No-MazeMisc-Repair)`: success_delta_pp=`0.000`, exp_delta=`392.889`, mean_time_overhead_ratio=`2.398234`

## Public Family Breakdown vs `CX3-D`
- `alpha_puzzle` / `CX27-F (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.846203`
- `alpha_puzzle` / `CX27-F (No-MazeMisc-Repair)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.833063`
- `bug_trap` / `CX27-F (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.738812`
- `bug_trap` / `CX27-F (No-MazeMisc-Repair)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.720237`
- `flange` / `CX27-F (Full)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.239155`
- `flange` / `CX27-F (No-MazeMisc-Repair)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.239992`
- `maze` / `CX27-F (Full)`: exp_delta=`-3.000`, mean_time_overhead_ratio=`2.775623`
- `maze` / `CX27-F (No-MazeMisc-Repair)`: exp_delta=`-113.000`, mean_time_overhead_ratio=`5.869857`
- `narrow_passage` / `CX27-F (Full)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.591953`
- `narrow_passage` / `CX27-F (No-MazeMisc-Repair)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.582088`
- `parasol_misc` / `CX27-F (Full)`: exp_delta=`-67.833`, mean_time_overhead_ratio=`3.643737`
- `parasol_misc` / `CX27-F (No-MazeMisc-Repair)`: exp_delta=`-58.333`, mean_time_overhead_ratio=`3.497069`

## Public vs `CX23-C (Full)`
- `CX27-F (Full)`: success_delta_pp=`0.000`, exp_delta=`2.944`, mean_time_overhead_ratio=`0.441106`
- `CX27-F (No-MazeMisc-Repair)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.440149`

## Public Family Breakdown vs `CX23-C (Full)`
- `alpha_puzzle` / `CX27-F (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.443413`
- `alpha_puzzle` / `CX27-F (No-MazeMisc-Repair)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.438482`
- `bug_trap` / `CX27-F (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.467809`
- `bug_trap` / `CX27-F (No-MazeMisc-Repair)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.460517`
- `flange` / `CX27-F (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.438760`
- `flange` / `CX27-F (No-MazeMisc-Repair)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.439132`
- `maze` / `CX27-F (Full)`: exp_delta=`110.000`, mean_time_overhead_ratio=`-0.201726`
- `maze` / `CX27-F (No-MazeMisc-Repair)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.452483`
- `narrow_passage` / `CX27-F (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.443202`
- `narrow_passage` / `CX27-F (No-MazeMisc-Repair)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.439238`
- `parasol_misc` / `CX27-F (Full)`: exp_delta=`-9.500`, mean_time_overhead_ratio=`0.507880`
- `parasol_misc` / `CX27-F (No-MazeMisc-Repair)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.460255`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`