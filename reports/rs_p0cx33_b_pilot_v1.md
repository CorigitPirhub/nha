# CX33-B Pilot V1

- protocol: frozen `CX32-B / Budgeted Slice Repair` parent; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; no hard-test evidence consumed
- chosen params: `{'maze_revisit_thr': 2, 'maze_stall_steps': 18, 'reverse_required_thr': 0.1, 'trap_thr': 0.54, 'turn_bridge_max': 0.1, 'turn_focus_max': 0.36, 'rescue_bridge_max': 0.08, 'rescue_focus_min': 0.39, 'rescue_path_min': 0.99, 'rescue_target': 'escape_border|reverse', 'rescue_budget': 1, 'suppress_bridge_min': 0.11, 'suppress_bridge_max': 0.13, 'suppress_focus_max': 0.31, 'suppress_path_min': 0.97, 'suppress_target': 'uncertain|none', 'stubborn_bridge_min': 0.125, 'stubborn_focus_max': 0.34, 'stubborn_path_max': 0.97, 'stubborn_target': 'forward_safe|forward_turn', 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 32, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24}`
- output root: `outputs/rs_p0cx33_b_pilot_v1`

## Public vs `CX3-D`
- `CX32-B (Full)`: success_delta_pp=`0.000`, exp_delta=`407.333`, mean_time_overhead_ratio=`2.421963`
- `CX33-B (Full)`: success_delta_pp=`0.000`, exp_delta=`411.444`, mean_time_overhead_ratio=`3.504408`
- `CX33-B (No-Stubborn-Uncertain-Turn)`: success_delta_pp=`0.000`, exp_delta=`391.111`, mean_time_overhead_ratio=`3.523954`

## Public Family Breakdown vs `CX3-D`
- `alpha_puzzle` / `CX32-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.861298`
- `alpha_puzzle` / `CX33-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.328395`
- `alpha_puzzle` / `CX33-B (No-Stubborn-Uncertain-Turn)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.325692`
- `bug_trap` / `CX32-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.743045`
- `bug_trap` / `CX33-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.192765`
- `bug_trap` / `CX33-B (No-Stubborn-Uncertain-Turn)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.198407`
- `flange` / `CX32-B (Full)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.273094`
- `flange` / `CX33-B (Full)`: exp_delta=`1421.000`, mean_time_overhead_ratio=`3.312233`
- `flange` / `CX33-B (No-Stubborn-Uncertain-Turn)`: exp_delta=`1421.000`, mean_time_overhead_ratio=`3.314418`
- `maze` / `CX32-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.753405`
- `maze` / `CX33-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`3.872242`
- `maze` / `CX33-B (No-Stubborn-Uncertain-Turn)`: exp_delta=`0.000`, mean_time_overhead_ratio=`3.902685`
- `narrow_passage` / `CX32-B (Full)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.619772`
- `narrow_passage` / `CX33-B (Full)`: exp_delta=`99.750`, mean_time_overhead_ratio=`3.761150`
- `narrow_passage` / `CX33-B (No-Stubborn-Uncertain-Turn)`: exp_delta=`99.750`, mean_time_overhead_ratio=`3.770906`
- `parasol_misc` / `CX32-B (Full)`: exp_delta=`-33.833`, mean_time_overhead_ratio=`3.370342`
- `parasol_misc` / `CX33-B (Full)`: exp_delta=`-16.333`, mean_time_overhead_ratio=`4.716537`
- `parasol_misc` / `CX33-B (No-Stubborn-Uncertain-Turn)`: exp_delta=`-77.333`, mean_time_overhead_ratio=`5.158460`

## Public vs `CX32-B (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-407.333`, mean_time_overhead_ratio=`-0.707770`
- `CX33-B (Full)`: success_delta_pp=`0.000`, exp_delta=`4.111`, mean_time_overhead_ratio=`0.316323`
- `CX33-B (No-Stubborn-Uncertain-Turn)`: success_delta_pp=`0.000`, exp_delta=`-16.222`, mean_time_overhead_ratio=`0.322035`

## Public Family Breakdown vs `CX32-B (Full)`
- `alpha_puzzle` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.741020`
- `alpha_puzzle` / `CX33-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.379949`
- `alpha_puzzle` / `CX33-B (No-Stubborn-Uncertain-Turn)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.379249`
- `bug_trap` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.732838`
- `bug_trap` / `CX33-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.387310`
- `bug_trap` / `CX33-B (No-Stubborn-Uncertain-Turn)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.388818`
- `flange` / `CX3-D`: exp_delta=`-1428.400`, mean_time_overhead_ratio=`-0.694479`
- `flange` / `CX33-B (Full)`: exp_delta=`-7.400`, mean_time_overhead_ratio=`0.317479`
- `flange` / `CX33-B (No-Stubborn-Uncertain-Turn)`: exp_delta=`-7.400`, mean_time_overhead_ratio=`0.318147`
- `maze` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.733575`
- `maze` / `CX33-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.298086`
- `maze` / `CX33-B (No-Stubborn-Uncertain-Turn)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.306197`
- `narrow_passage` / `CX3-D`: exp_delta=`-98.250`, mean_time_overhead_ratio=`-0.723740`
- `narrow_passage` / `CX33-B (Full)`: exp_delta=`1.500`, mean_time_overhead_ratio=`0.315317`
- `narrow_passage` / `CX33-B (No-Stubborn-Uncertain-Turn)`: exp_delta=`1.500`, mean_time_overhead_ratio=`0.318013`
- `parasol_misc` / `CX3-D`: exp_delta=`33.833`, mean_time_overhead_ratio=`-0.771185`
- `parasol_misc` / `CX33-B (Full)`: exp_delta=`17.500`, mean_time_overhead_ratio=`0.308030`
- `parasol_misc` / `CX33-B (No-Stubborn-Uncertain-Turn)`: exp_delta=`-43.500`, mean_time_overhead_ratio=`0.409148`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`