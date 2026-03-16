# CX28-C Pilot V1

- protocol: frozen `CX27-A / Maze Depression Guard` parent; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; no hard-test evidence consumed
- chosen params: `{'maze_revisit_thr': 2, 'maze_stall_steps': 18, 'reverse_required_thr': 0.1, 'trap_thr': 0.54, 'misc_revisit_thr': 1, 'misc_churn_thr': 0.15, 'misc_loop_thr': 0.06, 'scene_bonus_scale': 1.2, 'switch_margin': 0.01, 'block_ttl': 40, 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 32, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24}`
- output root: `outputs/rs_p0cx28_c_pilot_v1`

## Public vs `CX3-D`
- `CX28-C (Full)`: success_delta_pp=`0.000`, exp_delta=`392.611`, mean_time_overhead_ratio=`2.593292`
- `CX28-C (No-Scene-Arbitration)`: success_delta_pp=`0.000`, exp_delta=`399.167`, mean_time_overhead_ratio=`2.533217`

## Public Family Breakdown vs `CX3-D`
- `alpha_puzzle` / `CX28-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`3.104279`
- `alpha_puzzle` / `CX28-C (No-Scene-Arbitration)`: exp_delta=`0.000`, mean_time_overhead_ratio=`3.044733`
- `bug_trap` / `CX28-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.950552`
- `bug_trap` / `CX28-C (No-Scene-Arbitration)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.920516`
- `flange` / `CX28-C (Full)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.383693`
- `flange` / `CX28-C (No-Scene-Arbitration)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.366776`
- `maze` / `CX28-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.852558`
- `maze` / `CX28-C (No-Scene-Arbitration)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.854626`
- `narrow_passage` / `CX28-C (Full)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.762548`
- `narrow_passage` / `CX28-C (No-Scene-Arbitration)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.735106`
- `parasol_misc` / `CX28-C (Full)`: exp_delta=`-78.000`, mean_time_overhead_ratio=`4.970056`
- `parasol_misc` / `CX28-C (No-Scene-Arbitration)`: exp_delta=`-58.333`, mean_time_overhead_ratio=`3.777552`

## Public vs `CX27-A (Full)`
- `CX28-C (Full)`: success_delta_pp=`0.000`, exp_delta=`-6.556`, mean_time_overhead_ratio=`0.057399`
- `CX28-C (No-Scene-Arbitration)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.039721`

## Public Family Breakdown vs `CX27-A (Full)`
- `alpha_puzzle` / `CX28-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.066104`
- `alpha_puzzle` / `CX28-C (No-Scene-Arbitration)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.050637`
- `bug_trap` / `CX28-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.060252`
- `bug_trap` / `CX28-C (No-Scene-Arbitration)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.052190`
- `flange` / `CX28-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.042409`
- `flange` / `CX28-C (No-Scene-Arbitration)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.037197`
- `maze` / `CX28-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.043924`
- `maze` / `CX28-C (No-Scene-Arbitration)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.044484`
- `narrow_passage` / `CX28-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.047157`
- `narrow_passage` / `CX28-C (No-Scene-Arbitration)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.039520`
- `parasol_misc` / `CX28-C (Full)`: exp_delta=`-19.667`, mean_time_overhead_ratio=`0.344708`
- `parasol_misc` / `CX28-C (No-Scene-Arbitration)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.076106`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
