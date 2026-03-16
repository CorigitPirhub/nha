# CX32-B Pilot V1

- protocol: frozen `CX30-C / Low-Bridge + Focus Gate` parent; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; no hard-test evidence consumed
- chosen params: `{'maze_revisit_thr': 2, 'maze_stall_steps': 18, 'reverse_required_thr': 0.1, 'trap_thr': 0.54, 'turn_bridge_max': 0.1, 'turn_focus_max': 0.36, 'rescue_bridge_max': 0.08, 'rescue_focus_min': 0.39, 'rescue_path_min': 0.99, 'rescue_target': 'escape_border|reverse', 'rescue_budget': 1, 'suppress_bridge_min': 0.11, 'suppress_bridge_max': 0.13, 'suppress_focus_max': 0.31, 'suppress_path_min': 0.97, 'suppress_target': 'uncertain|none', 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 32, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24}`
- output root: `outputs/rs_p0cx32_b_pilot_v1`

## Public vs `CX3-D`
- `CX32-B (Full)`: success_delta_pp=`0.000`, exp_delta=`407.333`, mean_time_overhead_ratio=`2.421963`
- `CX32-B (No-Budgeted-Slice-Repair)`: success_delta_pp=`0.000`, exp_delta=`399.167`, mean_time_overhead_ratio=`2.432923`

## Public Family Breakdown vs `CX3-D`
- `alpha_puzzle` / `CX32-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.861298`
- `alpha_puzzle` / `CX32-B (No-Budgeted-Slice-Repair)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.907483`
- `bug_trap` / `CX32-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.743045`
- `bug_trap` / `CX32-B (No-Budgeted-Slice-Repair)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.763650`
- `flange` / `CX32-B (Full)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.273094`
- `flange` / `CX32-B (No-Budgeted-Slice-Repair)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.278287`
- `maze` / `CX32-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.753405`
- `maze` / `CX32-B (No-Budgeted-Slice-Repair)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.723265`
- `narrow_passage` / `CX32-B (Full)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.619772`
- `narrow_passage` / `CX32-B (No-Budgeted-Slice-Repair)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.616356`
- `parasol_misc` / `CX32-B (Full)`: exp_delta=`-33.833`, mean_time_overhead_ratio=`3.370342`
- `parasol_misc` / `CX32-B (No-Budgeted-Slice-Repair)`: exp_delta=`-58.333`, mean_time_overhead_ratio=`3.628519`

## Public vs `CX30-C (Full)`
- `CX32-B (Full)`: success_delta_pp=`0.000`, exp_delta=`5.889`, mean_time_overhead_ratio=`-0.008760`
- `CX32-B (No-Budgeted-Slice-Repair)`: success_delta_pp=`0.000`, exp_delta=`-2.278`, mean_time_overhead_ratio=`-0.005585`

## Public Family Breakdown vs `CX30-C (Full)`
- `alpha_puzzle` / `CX32-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.016717`
- `alpha_puzzle` / `CX32-B (No-Budgeted-Slice-Repair)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.004955`
- `bug_trap` / `CX32-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.008512`
- `bug_trap` / `CX32-B (No-Budgeted-Slice-Repair)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.003054`
- `flange` / `CX32-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.008255`
- `flange` / `CX32-B (No-Budgeted-Slice-Repair)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.006682`
- `maze` / `CX32-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.004013`
- `maze` / `CX32-B (No-Budgeted-Slice-Repair)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.004050`
- `narrow_passage` / `CX32-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.006558`
- `narrow_passage` / `CX32-B (No-Budgeted-Slice-Repair)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.007496`
- `parasol_misc` / `CX32-B (Full)`: exp_delta=`17.667`, mean_time_overhead_ratio=`-0.033014`
- `parasol_misc` / `CX32-B (No-Budgeted-Slice-Repair)`: exp_delta=`-6.833`, mean_time_overhead_ratio=`0.024111`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
