# CX28-A Pilot V1

- protocol: frozen `CX27-A / Maze Depression Guard` parent; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; no hard-test evidence consumed
- chosen params: `{'maze_revisit_thr': 2, 'maze_stall_steps': 18, 'reverse_required_thr': 0.1, 'trap_thr': 0.54, 'misc_revisit_thr': 1, 'misc_churn_thr': 0.2, 'misc_margin': 0.03, 'primitive_margin': 0.02, 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 32, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24}`
- output root: `outputs/rs_p0cx28_a_pilot_v1`

## Public vs `CX3-D`
- `CX28-A (Full)`: success_delta_pp=`0.000`, exp_delta=`397.056`, mean_time_overhead_ratio=`2.614938`
- `CX28-A (No-Misc-Review)`: success_delta_pp=`0.000`, exp_delta=`399.167`, mean_time_overhead_ratio=`2.590438`

## Public Family Breakdown vs `CX3-D`
- `alpha_puzzle` / `CX28-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.984063`
- `alpha_puzzle` / `CX28-A (No-Misc-Review)`: exp_delta=`0.000`, mean_time_overhead_ratio=`3.166650`
- `bug_trap` / `CX28-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.833143`
- `bug_trap` / `CX28-A (No-Misc-Review)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.977943`
- `flange` / `CX28-A (Full)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.448639`
- `flange` / `CX28-A (No-Misc-Review)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.415683`
- `maze` / `CX28-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.800056`
- `maze` / `CX28-A (No-Misc-Review)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.817666`
- `narrow_passage` / `CX28-A (Full)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.794043`
- `narrow_passage` / `CX28-A (No-Misc-Review)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.811512`
- `parasol_misc` / `CX28-A (Full)`: exp_delta=`-64.667`, mean_time_overhead_ratio=`4.079536`
- `parasol_misc` / `CX28-A (No-Misc-Review)`: exp_delta=`-58.333`, mean_time_overhead_ratio=`3.816527`

## Public vs `CX27-A (Full)`
- `CX28-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-2.111`, mean_time_overhead_ratio=`0.063769`
- `CX28-A (No-Misc-Review)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.056559`

## Public Family Breakdown vs `CX27-A (Full)`
- `alpha_puzzle` / `CX28-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.034878`
- `alpha_puzzle` / `CX28-A (No-Misc-Review)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.082306`
- `bug_trap` / `CX28-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.028741`
- `bug_trap` / `CX28-A (No-Misc-Review)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.067603`
- `flange` / `CX28-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.062416`
- `flange` / `CX28-A (No-Misc-Review)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.052264`
- `maze` / `CX28-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.029697`
- `maze` / `CX28-A (No-Misc-Review)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.034469`
- `narrow_passage` / `CX28-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.055922`
- `narrow_passage` / `CX28-A (No-Misc-Review)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.060784`
- `parasol_misc` / `CX28-A (Full)`: exp_delta=`-6.333`, mean_time_overhead_ratio=`0.144125`
- `parasol_misc` / `CX28-A (No-Misc-Review)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.084884`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
