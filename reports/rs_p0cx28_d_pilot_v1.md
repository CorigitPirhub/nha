# CX28-D Pilot V1

- protocol: frozen `CX27-A / Maze Depression Guard` parent; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; no hard-test evidence consumed
- chosen params: `{'maze_revisit_thr': 2, 'maze_stall_steps': 18, 'reverse_required_thr': 0.1, 'trap_thr': 0.54, 'misc_revisit_thr': 1, 'misc_churn_thr': 0.15, 'misc_loop_thr': 0.06, 'switch_margin': 0.01, 'block_ttl': 32, 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 32, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24}`
- output root: `outputs/rs_p0cx28_d_pilot_v1`

## Public vs `CX3-D`
- `CX28-D (Full)`: success_delta_pp=`0.000`, exp_delta=`400.556`, mean_time_overhead_ratio=`2.430974`
- `CX28-D (No-ForwardTurn-Arbitration)`: success_delta_pp=`0.000`, exp_delta=`399.167`, mean_time_overhead_ratio=`2.431324`

## Public Family Breakdown vs `CX3-D`
- `alpha_puzzle` / `CX28-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.902091`
- `alpha_puzzle` / `CX28-D (No-ForwardTurn-Arbitration)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.878510`
- `bug_trap` / `CX28-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.779462`
- `bug_trap` / `CX28-D (No-ForwardTurn-Arbitration)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.750826`
- `flange` / `CX28-D (Full)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.273502`
- `flange` / `CX28-D (No-ForwardTurn-Arbitration)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.271839`
- `maze` / `CX28-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.723461`
- `maze` / `CX28-D (No-ForwardTurn-Arbitration)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.736473`
- `narrow_passage` / `CX28-D (Full)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.615178`
- `narrow_passage` / `CX28-D (No-ForwardTurn-Arbitration)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.623869`
- `parasol_misc` / `CX28-D (Full)`: exp_delta=`-54.167`, mean_time_overhead_ratio=`3.673145`
- `parasol_misc` / `CX28-D (No-ForwardTurn-Arbitration)`: exp_delta=`-58.333`, mean_time_overhead_ratio=`3.632728`

## Public vs `CX27-A (Full)`
- `CX28-D (Full)`: success_delta_pp=`0.000`, exp_delta=`1.389`, mean_time_overhead_ratio=`0.009634`
- `CX28-D (No-ForwardTurn-Arbitration)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.009737`

## Public Family Breakdown vs `CX27-A (Full)`
- `alpha_puzzle` / `CX28-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.013585`
- `alpha_puzzle` / `CX28-D (No-ForwardTurn-Arbitration)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.007460`
- `bug_trap` / `CX28-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.014334`
- `bug_trap` / `CX28-D (No-ForwardTurn-Arbitration)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.006649`
- `flange` / `CX28-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.008462`
- `flange` / `CX28-D (No-ForwardTurn-Arbitration)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.007950`
- `maze` / `CX28-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.008942`
- `maze` / `CX28-D (No-ForwardTurn-Arbitration)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.012468`
- `narrow_passage` / `CX28-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.006142`
- `narrow_passage` / `CX28-D (No-ForwardTurn-Arbitration)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.008561`
- `parasol_misc` / `CX28-D (Full)`: exp_delta=`4.167`, mean_time_overhead_ratio=`0.052589`
- `parasol_misc` / `CX28-D (No-ForwardTurn-Arbitration)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.043485`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
