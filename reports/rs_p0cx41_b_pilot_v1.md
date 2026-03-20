# CX41-B Pilot V1

- protocol: frozen `CX40-A` parent on public evidence; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit
- chosen params: `{'turn_bridge_max': 0.1, 'turn_focus_max': 0.36, 'rescue_bridge_max': 0.08, 'rescue_focus_min': 0.39, 'rescue_path_min': 0.99, 'rescue_budget': 1, 'suppress_bridge_min': 0.11, 'suppress_bridge_max': 0.13, 'suppress_focus_max': 0.31, 'suppress_path_min': 0.97, 'stubborn_bridge_min': 0.125, 'stubborn_focus_max': 0.34, 'stubborn_path_max': 0.97, 'macro_bridge_min': 0.078, 'macro_bridge_max': 0.095, 'macro_focus_min': 0.34, 'macro_focus_max': 0.37, 'macro_path_min': 0.97, 'macro_path_max': 1.01, 'maze_revisit_thr': 2, 'maze_stall_steps': 18, 'reverse_required_thr': 0.1, 'trap_thr': 0.54, 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 32, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24, 'min_hits': 2, 'max_bridge_depth': 2, 'max_bridge_frontier': 3, 'max_review_targets': 3, 'max_screened_paths': 2, 'review_cell_stride': 2, 'review_yaw_bins': 12}`
- output root: `outputs/rs_p0cx41_b_pilot_v1`

## Public vs `CX40-A (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.899192`
- `CX36-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.759768`
- `CX39-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.063447`
- `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.630112`
- `CX41-B (No-Depth2-Escalation)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.468582`
- `CX41-B (No-Dominance-Gate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.280381`

## Public Family Breakdown vs `CX40-A (Full)`
- `alpha_puzzle` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.770828`
- `alpha_puzzle` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.384829`
- `alpha_puzzle` / `CX39-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.730548`
- `alpha_puzzle` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.006073`
- `alpha_puzzle` / `CX41-B (No-Depth2-Escalation)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.443565`
- `alpha_puzzle` / `CX41-B (No-Dominance-Gate)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.448555`
- `bug_trap` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.852152`
- `bug_trap` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.615229`
- `bug_trap` / `CX39-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.929084`
- `bug_trap` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.010357`
- `bug_trap` / `CX41-B (No-Depth2-Escalation)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.457548`
- `bug_trap` / `CX41-B (No-Dominance-Gate)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.441515`
- `flange` / `CX3-D`: exp_delta=`-1428.400`, mean_time_overhead_ratio=`-0.880668`
- `flange` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.731138`
- `flange` / `CX39-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.028653`
- `flange` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.592234`
- `flange` / `CX41-B (No-Depth2-Escalation)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.414150`
- `flange` / `CX41-B (No-Dominance-Gate)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.418947`
- `maze` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.938605`
- `maze` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.770303`
- `maze` / `CX39-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.141627`
- `maze` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.577238`
- `maze` / `CX41-B (No-Depth2-Escalation)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.389275`
- `maze` / `CX41-B (No-Dominance-Gate)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.003422`
- `narrow_passage` / `CX3-D`: exp_delta=`-98.250`, mean_time_overhead_ratio=`-0.919192`
- `narrow_passage` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.799651`
- `narrow_passage` / `CX39-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.117615`
- `narrow_passage` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.687696`
- `narrow_passage` / `CX41-B (No-Depth2-Escalation)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.550463`
- `narrow_passage` / `CX41-B (No-Dominance-Gate)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.131472`
- `parasol_misc` / `CX3-D`: exp_delta=`-12.333`, mean_time_overhead_ratio=`-0.936686`
- `parasol_misc` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.754423`
- `parasol_misc` / `CX39-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.011194`
- `parasol_misc` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.591577`
- `parasol_misc` / `CX41-B (No-Depth2-Escalation)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.419838`
- `parasol_misc` / `CX41-B (No-Dominance-Gate)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.004433`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`