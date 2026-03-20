# CX40-A Pilot V1

- protocol: frozen `CX39-C / Counterfactual Bridge Contract` parent on public evidence; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit
- research anchors:
  - Experience Graphs / reusable local bridge search: https://www.ri.cmu.edu/publications/experience-graphs-leveraging-multiple-planning-graphs-in-motion-planning/
  - SelectiveNet / selective expensive-evaluation abstention: https://proceedings.mlr.press/v97/geifman19a.html
  - Learning model preconditions / initiation-set style gating: https://proceedings.mlr.press/v164/ravichandar22a.html
- chosen params: `{'turn_bridge_max': 0.1, 'turn_focus_max': 0.36, 'rescue_bridge_max': 0.08, 'rescue_focus_min': 0.39, 'rescue_path_min': 0.99, 'rescue_budget': 1, 'suppress_bridge_min': 0.11, 'suppress_bridge_max': 0.13, 'suppress_focus_max': 0.31, 'suppress_path_min': 0.97, 'stubborn_bridge_min': 0.125, 'stubborn_focus_max': 0.34, 'stubborn_path_max': 0.97, 'macro_bridge_min': 0.078, 'macro_bridge_max': 0.095, 'macro_focus_min': 0.34, 'macro_focus_max': 0.37, 'macro_path_min': 0.97, 'macro_path_max': 1.01, 'maze_revisit_thr': 2, 'maze_stall_steps': 18, 'reverse_required_thr': 0.1, 'trap_thr': 0.54, 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 32, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24, 'min_hits': 2, 'max_bridge_depth': 2, 'max_bridge_frontier': 3, 'max_review_targets': 3, 'max_screened_paths': 2}`
- output root: `outputs/rs_p0cx40_a_pilot_v1`

## Public vs `CX39-C (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.951146`
- `CX36-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.883577`
- `CX40-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.515374`
- `CX40-A (No-Depth2-Escalation)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.515285`
- `CX40-A (No-Prescreener)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.269865`

## Public Family Breakdown vs `CX39-C (Full)`
- `alpha_puzzle` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.867573`
- `alpha_puzzle` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.644522`
- `alpha_puzzle` / `CX40-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.422149`
- `alpha_puzzle` / `CX40-A (No-Depth2-Escalation)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.419814`
- `alpha_puzzle` / `CX40-A (No-Prescreener)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.305255`
- `bug_trap` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.923359`
- `bug_trap` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.800542`
- `bug_trap` / `CX40-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.481619`
- `bug_trap` / `CX40-A (No-Depth2-Escalation)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.482761`
- `bug_trap` / `CX40-A (No-Prescreener)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.298280`
- `flange` / `CX3-D`: exp_delta=`-1428.400`, mean_time_overhead_ratio=`-0.941177`
- `flange` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.867468`
- `flange` / `CX40-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.507062`
- `flange` / `CX40-A (No-Depth2-Escalation)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.508277`
- `flange` / `CX40-A (No-Prescreener)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.270448`
- `maze` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.971332`
- `maze` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.892747`
- `maze` / `CX40-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.533065`
- `maze` / `CX40-A (No-Depth2-Escalation)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.529178`
- `maze` / `CX40-A (No-Prescreener)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.299987`
- `narrow_passage` / `CX3-D`: exp_delta=`-98.250`, mean_time_overhead_ratio=`-0.961840`
- `narrow_passage` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.905389`
- `narrow_passage` / `CX40-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.527771`
- `narrow_passage` / `CX40-A (No-Depth2-Escalation)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.525764`
- `narrow_passage` / `CX40-A (No-Prescreener)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.268939`
- `parasol_misc` / `CX3-D`: exp_delta=`-12.333`, mean_time_overhead_ratio=`-0.968519`
- `parasol_misc` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.877895`
- `parasol_misc` / `CX40-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.502783`
- `parasol_misc` / `CX40-A (No-Depth2-Escalation)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.504555`
- `parasol_misc` / `CX40-A (No-Prescreener)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.269366`

## Public vs `CX36-B (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.580371`
- `CX39-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`7.589385`
- `CX40-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`3.162640`
- `CX40-A (No-Depth2-Escalation)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`3.163400`
- `CX40-A (No-Prescreener)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`5.271415`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`