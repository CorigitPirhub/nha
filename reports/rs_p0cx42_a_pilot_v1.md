# CX42-A Pilot V1

- protocol: frozen `CX34-A / Subtype-Specific Macro Rescue` parent; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit
- chosen params: `{'turn_bridge_max': 0.1, 'turn_focus_max': 0.36, 'rescue_bridge_max': 0.08, 'rescue_focus_min': 0.39, 'rescue_path_min': 0.99, 'rescue_budget': 1, 'suppress_bridge_min': 0.11, 'suppress_bridge_max': 0.13, 'suppress_focus_max': 0.31, 'suppress_path_min': 0.97, 'stubborn_bridge_min': 0.125, 'stubborn_focus_max': 0.34, 'stubborn_path_max': 0.97, 'macro_bridge_min': 0.075, 'macro_bridge_max': 0.095, 'macro_focus_min': 0.34, 'macro_focus_max': 0.37, 'macro_path_min': 0.97, 'macro_path_max': 1.01, 'maze_revisit_thr': 2, 'maze_stall_steps': 18, 'reverse_required_thr': 0.1, 'trap_thr': 0.54, 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 32, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24, 'review_cell_stride': 2, 'review_yaw_bins': 12}`
- output root: `outputs/rs_p0cx42_a_pilot_v1`

## Public vs `CX3-D`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`420.389`, mean_time_overhead_ratio=`3.527234`
- `CX42-A (Full)`: success_delta_pp=`0.000`, exp_delta=`99.889`, mean_time_overhead_ratio=`0.444926`
- `CX42-A (No-Dominance-Compatibility)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`1.339339`

## Public Family Breakdown vs `CX3-D`
- `alpha_puzzle` / `CX34-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.323819`
- `alpha_puzzle` / `CX42-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.148991`
- `alpha_puzzle` / `CX42-A (No-Dominance-Compatibility)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.690892`
- `bug_trap` / `CX34-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.307586`
- `bug_trap` / `CX42-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.398726`
- `bug_trap` / `CX42-A (No-Dominance-Compatibility)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.593804`
- `flange` / `CX34-A (Full)`: exp_delta=`1421.000`, mean_time_overhead_ratio=`3.336465`
- `flange` / `CX42-A (Full)`: exp_delta=`387.000`, mean_time_overhead_ratio=`0.414827`
- `flange` / `CX42-A (No-Dominance-Compatibility)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`1.243678`
- `maze` / `CX34-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`3.914200`
- `maze` / `CX42-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.746913`
- `maze` / `CX42-A (No-Dominance-Compatibility)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.525259`
- `narrow_passage` / `CX34-A (Full)`: exp_delta=`99.750`, mean_time_overhead_ratio=`3.789361`
- `narrow_passage` / `CX42-A (Full)`: exp_delta=`-44.500`, mean_time_overhead_ratio=`0.462308`
- `narrow_passage` / `CX42-A (No-Dominance-Compatibility)`: exp_delta=`98.250`, mean_time_overhead_ratio=`1.471141`
- `parasol_misc` / `CX34-A (Full)`: exp_delta=`10.500`, mean_time_overhead_ratio=`4.660825`
- `parasol_misc` / `CX42-A (Full)`: exp_delta=`6.833`, mean_time_overhead_ratio=`0.832447`
- `parasol_misc` / `CX42-A (No-Dominance-Compatibility)`: exp_delta=`12.333`, mean_time_overhead_ratio=`1.905372`

## Public vs `CX34-A (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-420.389`, mean_time_overhead_ratio=`-0.779115`
- `CX42-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-320.500`, mean_time_overhead_ratio=`-0.680837`
- `CX42-A (No-Dominance-Compatibility)`: success_delta_pp=`0.000`, exp_delta=`2.333`, mean_time_overhead_ratio=`-0.483274`

## Public Family Breakdown vs `CX34-A (Full)`
- `alpha_puzzle` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.812165`
- `alpha_puzzle` / `CX42-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.596344`
- `alpha_puzzle` / `CX42-A (No-Dominance-Compatibility)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.494556`
- `bug_trap` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.811590`
- `bug_trap` / `CX42-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.548057`
- `bug_trap` / `CX42-A (No-Dominance-Compatibility)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.511302`
- `flange` / `CX3-D`: exp_delta=`-1421.000`, mean_time_overhead_ratio=`-0.769397`
- `flange` / `CX42-A (Full)`: exp_delta=`-1034.000`, mean_time_overhead_ratio=`-0.673737`
- `flange` / `CX42-A (No-Dominance-Compatibility)`: exp_delta=`7.400`, mean_time_overhead_ratio=`-0.482602`
- `maze` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.796508`
- `maze` / `CX42-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.644517`
- `maze` / `CX42-A (No-Dominance-Compatibility)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.486130`
- `narrow_passage` / `CX3-D`: exp_delta=`-99.750`, mean_time_overhead_ratio=`-0.791204`
- `narrow_passage` / `CX42-A (Full)`: exp_delta=`-144.250`, mean_time_overhead_ratio=`-0.694676`
- `narrow_passage` / `CX42-A (No-Dominance-Compatibility)`: exp_delta=`-1.500`, mean_time_overhead_ratio=`-0.484035`
- `parasol_misc` / `CX3-D`: exp_delta=`-10.500`, mean_time_overhead_ratio=`-0.823347`
- `parasol_misc` / `CX42-A (Full)`: exp_delta=`-3.667`, mean_time_overhead_ratio=`-0.676293`
- `parasol_misc` / `CX42-A (No-Dominance-Compatibility)`: exp_delta=`1.833`, mean_time_overhead_ratio=`-0.486758`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`