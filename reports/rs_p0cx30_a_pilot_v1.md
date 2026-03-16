# CX30-A Pilot V1

- protocol: frozen `CX29-D / Aux-Calibrated Bridge Threshold` parent; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; no hard-test evidence consumed
- chosen params: `{'maze_revisit_thr': 2, 'maze_stall_steps': 18, 'reverse_required_thr': 0.1, 'trap_thr': 0.54, 'bridge_low': 0.09, 'bridge_high': 0.145, 'path_openness_thr': 0.97, 'focus_gap_thr': 0.36, 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 32, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24}`
- output root: `outputs/rs_p0cx30_a_pilot_v1`

## Public vs `CX3-D`
- `CX30-A (Full)`: success_delta_pp=`0.000`, exp_delta=`401.389`, mean_time_overhead_ratio=`2.468610`
- `CX30-A (No-Path-Open-Refine)`: success_delta_pp=`0.000`, exp_delta=`399.167`, mean_time_overhead_ratio=`2.499936`

## Public Family Breakdown vs `CX3-D`
- `alpha_puzzle` / `CX30-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.930968`
- `alpha_puzzle` / `CX30-A (No-Path-Open-Refine)`: exp_delta=`0.000`, mean_time_overhead_ratio=`3.020115`
- `bug_trap` / `CX30-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.817774`
- `bug_trap` / `CX30-A (No-Path-Open-Refine)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.811402`
- `flange` / `CX30-A (Full)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.311295`
- `flange` / `CX30-A (No-Path-Open-Refine)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.344444`
- `maze` / `CX30-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.786730`
- `maze` / `CX30-A (No-Path-Open-Refine)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.761562`
- `narrow_passage` / `CX30-A (Full)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.668361`
- `narrow_passage` / `CX30-A (No-Path-Open-Refine)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.687288`
- `parasol_misc` / `CX30-A (Full)`: exp_delta=`-51.667`, mean_time_overhead_ratio=`3.559931`
- `parasol_misc` / `CX30-A (No-Path-Open-Refine)`: exp_delta=`-58.333`, mean_time_overhead_ratio=`3.676102`

## Public vs `CX29-D (Full)`
- `CX30-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.667`, mean_time_overhead_ratio=`0.006856`
- `CX30-A (No-Path-Open-Refine)`: success_delta_pp=`0.000`, exp_delta=`-1.556`, mean_time_overhead_ratio=`0.015949`

## Public Family Breakdown vs `CX29-D (Full)`
- `alpha_puzzle` / `CX30-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.000843`
- `alpha_puzzle` / `CX30-A (No-Path-Open-Refine)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.023540`
- `bug_trap` / `CX30-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.001895`
- `bug_trap` / `CX30-A (No-Path-Open-Refine)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.000223`
- `flange` / `CX30-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.008482`
- `flange` / `CX30-A (No-Path-Open-Refine)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.018578`
- `maze` / `CX30-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.016125`
- `maze` / `CX30-A (No-Path-Open-Refine)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.009371`
- `narrow_passage` / `CX30-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.006432`
- `narrow_passage` / `CX30-A (No-Path-Open-Refine)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.011625`
- `parasol_misc` / `CX30-A (Full)`: exp_delta=`2.000`, mean_time_overhead_ratio=`-0.012355`
- `parasol_misc` / `CX30-A (No-Path-Open-Refine)`: exp_delta=`-4.667`, mean_time_overhead_ratio=`0.012807`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
