# CX33-A Pilot V1

- protocol: frozen `CX32-B / Budgeted Slice Repair` parent; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; no hard-test evidence consumed
- chosen params: `{'maze_revisit_thr': 2, 'maze_stall_steps': 18, 'reverse_required_thr': 0.1, 'trap_thr': 0.54, 'turn_bridge_max': 0.1, 'turn_focus_max': 0.36, 'rescue_bridge_max': 0.08, 'rescue_focus_min': 0.39, 'rescue_path_min': 0.99, 'rescue_target': 'reverse_setup|reverse', 'suppress_bridge_min': 0.11, 'suppress_bridge_max': 0.13, 'suppress_focus_max': 0.31, 'suppress_path_min': 0.97, 'suppress_target': 'uncertain|none', 'stubborn_bridge_min': 0.125, 'stubborn_focus_max': 0.34, 'stubborn_path_max': 0.97, 'stubborn_target': 'forward_safe|forward_turn', 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 32, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24}`
- output root: `outputs/rs_p0cx33_a_pilot_v1`

## Public vs `CX3-D`
- `CX32-B (Full)`: success_delta_pp=`0.000`, exp_delta=`407.333`, mean_time_overhead_ratio=`2.421963`
- `CX33-A (Full)`: success_delta_pp=`0.000`, exp_delta=`408.500`, mean_time_overhead_ratio=`2.087175`
- `CX33-A (No-Stubborn-Slice)`: success_delta_pp=`0.000`, exp_delta=`388.167`, mean_time_overhead_ratio=`2.111612`

## Public Family Breakdown vs `CX3-D`
- `alpha_puzzle` / `CX32-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.861298`
- `alpha_puzzle` / `CX33-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.613530`
- `alpha_puzzle` / `CX33-A (No-Stubborn-Slice)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.657231`
- `bug_trap` / `CX32-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.743045`
- `bug_trap` / `CX33-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.546622`
- `bug_trap` / `CX33-A (No-Stubborn-Slice)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.539717`
- `flange` / `CX32-B (Full)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.273094`
- `flange` / `CX33-A (Full)`: exp_delta=`1421.000`, mean_time_overhead_ratio=`1.946792`
- `flange` / `CX33-A (No-Stubborn-Slice)`: exp_delta=`1421.000`, mean_time_overhead_ratio=`1.967310`
- `maze` / `CX32-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.753405`
- `maze` / `CX33-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.317352`
- `maze` / `CX33-A (No-Stubborn-Slice)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.323633`
- `narrow_passage` / `CX32-B (Full)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.619772`
- `narrow_passage` / `CX33-A (Full)`: exp_delta=`99.750`, mean_time_overhead_ratio=`2.260773`
- `narrow_passage` / `CX33-A (No-Stubborn-Slice)`: exp_delta=`99.750`, mean_time_overhead_ratio=`2.267548`
- `parasol_misc` / `CX32-B (Full)`: exp_delta=`-33.833`, mean_time_overhead_ratio=`3.370342`
- `parasol_misc` / `CX33-A (Full)`: exp_delta=`-25.167`, mean_time_overhead_ratio=`3.106671`
- `parasol_misc` / `CX33-A (No-Stubborn-Slice)`: exp_delta=`-86.167`, mean_time_overhead_ratio=`3.373127`

## Public vs `CX32-B (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-407.333`, mean_time_overhead_ratio=`-0.707770`
- `CX33-A (Full)`: success_delta_pp=`0.000`, exp_delta=`1.167`, mean_time_overhead_ratio=`-0.097835`
- `CX33-A (No-Stubborn-Slice)`: success_delta_pp=`0.000`, exp_delta=`-19.167`, mean_time_overhead_ratio=`-0.090694`

## Public Family Breakdown vs `CX32-B (Full)`
- `alpha_puzzle` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.741020`
- `alpha_puzzle` / `CX33-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.064167`
- `alpha_puzzle` / `CX33-A (No-Stubborn-Slice)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.052849`
- `bug_trap` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.732838`
- `bug_trap` / `CX33-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.052477`
- `bug_trap` / `CX33-A (No-Stubborn-Slice)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.054322`
- `flange` / `CX3-D`: exp_delta=`-1428.400`, mean_time_overhead_ratio=`-0.694479`
- `flange` / `CX33-A (Full)`: exp_delta=`-7.400`, mean_time_overhead_ratio=`-0.099692`
- `flange` / `CX33-A (No-Stubborn-Slice)`: exp_delta=`-7.400`, mean_time_overhead_ratio=`-0.093424`
- `maze` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.733575`
- `maze` / `CX33-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.116175`
- `maze` / `CX33-A (No-Stubborn-Slice)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.114502`
- `narrow_passage` / `CX3-D`: exp_delta=`-98.250`, mean_time_overhead_ratio=`-0.723740`
- `narrow_passage` / `CX33-A (Full)`: exp_delta=`1.500`, mean_time_overhead_ratio=`-0.099177`
- `narrow_passage` / `CX33-A (No-Stubborn-Slice)`: exp_delta=`1.500`, mean_time_overhead_ratio=`-0.097306`
- `parasol_misc` / `CX3-D`: exp_delta=`33.833`, mean_time_overhead_ratio=`-0.771185`
- `parasol_misc` / `CX33-A (Full)`: exp_delta=`8.667`, mean_time_overhead_ratio=`-0.060332`
- `parasol_misc` / `CX33-A (No-Stubborn-Slice)`: exp_delta=`-52.333`, mean_time_overhead_ratio=`0.000637`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`