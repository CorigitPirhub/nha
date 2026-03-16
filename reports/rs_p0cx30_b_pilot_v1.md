# CX30-B Pilot V1

- protocol: frozen `CX29-D / Aux-Calibrated Bridge Threshold` parent; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; no hard-test evidence consumed
- chosen params: `{'maze_revisit_thr': 2, 'maze_stall_steps': 18, 'reverse_required_thr': 0.1, 'trap_thr': 0.54, 'tree_depth': 2, 'gain_margin': 0.02, 'prob_thr': 0.5, 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 32, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24}`
- output root: `outputs/rs_p0cx30_b_pilot_v1`

## Public vs `CX3-D`
- `CX30-B (Full)`: success_delta_pp=`0.000`, exp_delta=`401.278`, mean_time_overhead_ratio=`2.460467`
- `CX30-B (No-Aux-Tree)`: success_delta_pp=`0.000`, exp_delta=`399.167`, mean_time_overhead_ratio=`2.468368`

## Public Family Breakdown vs `CX3-D`
- `alpha_puzzle` / `CX30-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.943589`
- `alpha_puzzle` / `CX30-B (No-Aux-Tree)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.956262`
- `bug_trap` / `CX30-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.799212`
- `bug_trap` / `CX30-B (No-Aux-Tree)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.812267`
- `flange` / `CX30-B (Full)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.305716`
- `flange` / `CX30-B (No-Aux-Tree)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.307801`
- `maze` / `CX30-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.765919`
- `maze` / `CX30-B (No-Aux-Tree)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.769426`
- `narrow_passage` / `CX30-B (Full)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.660758`
- `narrow_passage` / `CX30-B (No-Aux-Tree)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.662864`
- `parasol_misc` / `CX30-B (Full)`: exp_delta=`-52.000`, mean_time_overhead_ratio=`3.498437`
- `parasol_misc` / `CX30-B (No-Aux-Tree)`: exp_delta=`-58.333`, mean_time_overhead_ratio=`3.671857`

## Public vs `CX29-D (Full)`
- `CX30-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.556`, mean_time_overhead_ratio=`0.004492`
- `CX30-B (No-Aux-Tree)`: success_delta_pp=`0.000`, exp_delta=`-1.556`, mean_time_overhead_ratio=`0.006785`

## Public Family Breakdown vs `CX29-D (Full)`
- `alpha_puzzle` / `CX30-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.004056`
- `alpha_puzzle` / `CX30-B (No-Aux-Tree)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.007283`
- `bug_trap` / `CX30-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.002976`
- `bug_trap` / `CX30-B (No-Aux-Tree)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.000450`
- `flange` / `CX30-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.006783`
- `flange` / `CX30-B (No-Aux-Tree)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.007418`
- `maze` / `CX30-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.010541`
- `maze` / `CX30-B (No-Aux-Tree)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.011482`
- `narrow_passage` / `CX30-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.004346`
- `narrow_passage` / `CX30-B (No-Aux-Tree)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.004924`
- `parasol_misc` / `CX30-B (Full)`: exp_delta=`1.667`, mean_time_overhead_ratio=`-0.025674`
- `parasol_misc` / `CX30-B (No-Aux-Tree)`: exp_delta=`-4.667`, mean_time_overhead_ratio=`0.011887`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
