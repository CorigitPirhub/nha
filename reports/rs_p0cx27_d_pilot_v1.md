# CX27-D Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; this round stayed public-first and did not consume hard-test evidence
- chosen params: `{'maze_revisit_thr': 2, 'maze_stall_steps': 14, 'misc_revisit_thr': 1, 'misc_churn_thr': 0.35, 'reverse_required_thr': 0.08, 'trap_thr': 0.5, 'progress_eps': 0.02, 'commit_fail_margin': 0.04, 'failure_ttl': 32, 'misc_global_ttl': 64, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24}`
- output root: `outputs/rs_p0cx27_d_pilot_v1`

## Public vs `CX3-D`
- `CX27-D (Full)`: success_delta_pp=`0.000`, exp_delta=`384.722`, mean_time_overhead_ratio=`2.533672`
- `CX27-D (No-Global-Cooldown)`: success_delta_pp=`0.000`, exp_delta=`392.889`, mean_time_overhead_ratio=`2.566427`

## Public Family Breakdown vs `CX3-D`
- `alpha_puzzle` / `CX27-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.952041`
- `alpha_puzzle` / `CX27-D (No-Global-Cooldown)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.972814`
- `bug_trap` / `CX27-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.755623`
- `bug_trap` / `CX27-D (No-Global-Cooldown)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.830200`
- `flange` / `CX27-D (Full)`: exp_delta=`1377.400`, mean_time_overhead_ratio=`2.377319`
- `flange` / `CX27-D (No-Global-Cooldown)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.402637`
- `maze` / `CX27-D (Full)`: exp_delta=`-3.000`, mean_time_overhead_ratio=`2.760970`
- `maze` / `CX27-D (No-Global-Cooldown)`: exp_delta=`-113.000`, mean_time_overhead_ratio=`6.063562`
- `narrow_passage` / `CX27-D (Full)`: exp_delta=`98.000`, mean_time_overhead_ratio=`2.737750`
- `narrow_passage` / `CX27-D (No-Global-Cooldown)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.767138`
- `parasol_misc` / `CX27-D (Full)`: exp_delta=`-58.500`, mean_time_overhead_ratio=`3.571026`
- `parasol_misc` / `CX27-D (No-Global-Cooldown)`: exp_delta=`-58.333`, mean_time_overhead_ratio=`3.610886`

## Public vs `CX23-C (Full)`
- `CX27-D (Full)`: success_delta_pp=`0.000`, exp_delta=`-8.167`, mean_time_overhead_ratio=`0.497547`
- `CX27-D (No-Global-Cooldown)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.511428`

## Public Family Breakdown vs `CX23-C (Full)`
- `alpha_puzzle` / `CX27-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.483132`
- `alpha_puzzle` / `CX27-D (No-Global-Cooldown)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.490928`
- `bug_trap` / `CX27-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.474409`
- `bug_trap` / `CX27-D (No-Global-Cooldown)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.503687`
- `flange` / `CX27-D (Full)`: exp_delta=`-51.000`, mean_time_overhead_ratio=`0.500130`
- `flange` / `CX27-D (No-Global-Cooldown)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.511375`
- `maze` / `CX27-D (Full)`: exp_delta=`110.000`, mean_time_overhead_ratio=`-0.204824`
- `maze` / `CX27-D (No-Global-Cooldown)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.493437`
- `narrow_passage` / `CX27-D (Full)`: exp_delta=`-0.250`, mean_time_overhead_ratio=`0.501781`
- `narrow_passage` / `CX27-D (No-Global-Cooldown)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.513589`
- `parasol_misc` / `CX27-D (Full)`: exp_delta=`-0.167`, mean_time_overhead_ratio=`0.484270`
- `parasol_misc` / `CX27-D (No-Global-Cooldown)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.497213`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`