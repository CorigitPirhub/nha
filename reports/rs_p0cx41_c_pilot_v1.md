# CX41-C Pilot V1

- protocol: frozen `CX40-A` parent on public evidence; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit
- chosen params: `{'turn_bridge_max': 0.1, 'turn_focus_max': 0.36, 'rescue_bridge_max': 0.08, 'rescue_focus_min': 0.39, 'rescue_path_min': 0.99, 'rescue_budget': 1, 'suppress_bridge_min': 0.11, 'suppress_bridge_max': 0.13, 'suppress_focus_max': 0.31, 'suppress_path_min': 0.97, 'stubborn_bridge_min': 0.125, 'stubborn_focus_max': 0.34, 'stubborn_path_max': 0.97, 'macro_bridge_min': 0.078, 'macro_bridge_max': 0.095, 'macro_focus_min': 0.34, 'macro_focus_max': 0.37, 'macro_path_min': 0.97, 'macro_path_max': 1.01, 'maze_revisit_thr': 2, 'maze_stall_steps': 18, 'reverse_required_thr': 0.1, 'trap_thr': 0.54, 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 32, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24, 'min_hits': 2, 'max_bridge_depth': 2, 'max_bridge_frontier': 3, 'max_review_targets': 3, 'max_screened_paths': 2, 'review_cell_stride': 2, 'review_yaw_bins': 12}`
- output root: `outputs/rs_p0cx41_c_pilot_v1`

## Public vs `CX40-A (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.899192`
- `CX36-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.759768`
- `CX39-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.063447`
- `CX41-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.640887`
- `CX41-C (No-Disagreement-Gate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.644865`
- `CX41-C (No-Dominance-Gate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.433626`

## Public Family Breakdown vs `CX40-A (Full)`
- `alpha_puzzle` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.770828`
- `alpha_puzzle` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.384829`
- `alpha_puzzle` / `CX39-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.730548`
- `alpha_puzzle` / `CX41-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.043850`
- `alpha_puzzle` / `CX41-C (No-Disagreement-Gate)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.082896`
- `alpha_puzzle` / `CX41-C (No-Dominance-Gate)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.024705`
- `bug_trap` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.852152`
- `bug_trap` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.615229`
- `bug_trap` / `CX39-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.929084`
- `bug_trap` / `CX41-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.388401`
- `bug_trap` / `CX41-C (No-Disagreement-Gate)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.418703`
- `bug_trap` / `CX41-C (No-Dominance-Gate)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.041847`
- `flange` / `CX3-D`: exp_delta=`-1428.400`, mean_time_overhead_ratio=`-0.880668`
- `flange` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.731138`
- `flange` / `CX39-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.028653`
- `flange` / `CX41-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.593468`
- `flange` / `CX41-C (No-Disagreement-Gate)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.597615`
- `flange` / `CX41-C (No-Dominance-Gate)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.412382`
- `maze` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.938605`
- `maze` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.770303`
- `maze` / `CX39-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.141627`
- `maze` / `CX41-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.759365`
- `maze` / `CX41-C (No-Disagreement-Gate)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.766065`
- `maze` / `CX41-C (No-Dominance-Gate)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.436190`
- `narrow_passage` / `CX3-D`: exp_delta=`-98.250`, mean_time_overhead_ratio=`-0.919192`
- `narrow_passage` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.799651`
- `narrow_passage` / `CX39-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.117615`
- `narrow_passage` / `CX41-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.696688`
- `narrow_passage` / `CX41-C (No-Disagreement-Gate)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.700073`
- `narrow_passage` / `CX41-C (No-Dominance-Gate)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.584456`
- `parasol_misc` / `CX3-D`: exp_delta=`-12.333`, mean_time_overhead_ratio=`-0.936686`
- `parasol_misc` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.754423`
- `parasol_misc` / `CX39-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.011194`
- `parasol_misc` / `CX41-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.702500`
- `parasol_misc` / `CX41-C (No-Disagreement-Gate)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.708930`
- `parasol_misc` / `CX41-C (No-Dominance-Gate)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.419472`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`