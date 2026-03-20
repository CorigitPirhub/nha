# CX39-B Pilot V1

- protocol: frozen `CX36-B / Event-Triggered Compatibility Extension` parent on public evidence; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit
- research anchors:
  - Experience Graphs / reusable local bridge search: https://www.ri.cmu.edu/publications/experience-graphs-leveraging-multiple-planning-graphs-in-motion-planning/
  - Prioritized sweeping / targeted review scheduling: https://proceedings.neurips.cc/paper_files/paper/1992/file/55743cc0393b1cb4b8b37d09ae48d097-Paper.pdf
  - Learning model preconditions / initiation-set style gating: https://proceedings.mlr.press/v164/ravichandar22a.html
- chosen params: `{'turn_bridge_max': 0.1, 'turn_focus_max': 0.36, 'rescue_bridge_max': 0.08, 'rescue_focus_min': 0.39, 'rescue_path_min': 0.99, 'rescue_budget': 1, 'suppress_bridge_min': 0.11, 'suppress_bridge_max': 0.13, 'suppress_focus_max': 0.31, 'suppress_path_min': 0.97, 'stubborn_bridge_min': 0.125, 'stubborn_focus_max': 0.34, 'stubborn_path_max': 0.97, 'macro_bridge_min': 0.078, 'macro_bridge_max': 0.095, 'macro_focus_min': 0.34, 'macro_focus_max': 0.37, 'macro_path_min': 0.97, 'macro_path_max': 1.01, 'maze_revisit_thr': 2, 'maze_stall_steps': 18, 'reverse_required_thr': 0.1, 'trap_thr': 0.54, 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 32, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24, 'min_hits': 2, 'max_bridge_depth': 2, 'max_bridge_frontier': 3, 'max_review_targets': 3}`
- output root: `outputs/rs_p0cx39_b_pilot_v1`

## Public vs `CX3-D`
- `CX36-B (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.508881`
- `CX39-B (Full)`: success_delta_pp=`0.000`, exp_delta=`413.278`, mean_time_overhead_ratio=`12.055369`
- `CX39-B (No-Compatibility-Witness)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`6.627744`
- `CX39-B (No-Depth2-Bridge)`: success_delta_pp=`0.000`, exp_delta=`414.667`, mean_time_overhead_ratio=`6.512677`

## Public Family Breakdown vs `CX3-D`
- `alpha_puzzle` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.962622`
- `alpha_puzzle` / `CX39-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.975295`
- `alpha_puzzle` / `CX39-B (No-Compatibility-Witness)`: exp_delta=`0.000`, mean_time_overhead_ratio=`3.801917`
- `alpha_puzzle` / `CX39-B (No-Depth2-Bridge)`: exp_delta=`0.000`, mean_time_overhead_ratio=`3.958100`
- `bug_trap` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.845261`
- `bug_trap` / `CX39-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`7.962713`
- `bug_trap` / `CX39-B (No-Compatibility-Witness)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.990814`
- `bug_trap` / `CX39-B (No-Depth2-Bridge)`: exp_delta=`0.000`, mean_time_overhead_ratio=`5.098211`
- `flange` / `CX36-B (Full)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.311918`
- `flange` / `CX39-B (Full)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`9.995626`
- `flange` / `CX39-B (No-Compatibility-Witness)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`5.462037`
- `flange` / `CX39-B (No-Depth2-Bridge)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`5.554854`
- `maze` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.486218`
- `maze` / `CX39-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`20.500372`
- `maze` / `CX39-B (No-Compatibility-Witness)`: exp_delta=`0.000`, mean_time_overhead_ratio=`20.817024`
- `maze` / `CX39-B (No-Depth2-Bridge)`: exp_delta=`0.000`, mean_time_overhead_ratio=`10.355379`
- `narrow_passage` / `CX36-B (Full)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.671282`
- `narrow_passage` / `CX39-B (Full)`: exp_delta=`55.750`, mean_time_overhead_ratio=`15.591638`
- `narrow_passage` / `CX39-B (No-Compatibility-Witness)`: exp_delta=`98.250`, mean_time_overhead_ratio=`7.737172`
- `narrow_passage` / `CX39-B (No-Depth2-Bridge)`: exp_delta=`62.000`, mean_time_overhead_ratio=`8.136021`
- `parasol_misc` / `CX36-B (Full)`: exp_delta=`12.333`, mean_time_overhead_ratio=`4.622823`
- `parasol_misc` / `CX39-B (Full)`: exp_delta=`12.333`, mean_time_overhead_ratio=`17.537399`
- `parasol_misc` / `CX39-B (No-Compatibility-Witness)`: exp_delta=`12.333`, mean_time_overhead_ratio=`17.653981`
- `parasol_misc` / `CX39-B (No-Depth2-Bridge)`: exp_delta=`12.333`, mean_time_overhead_ratio=`9.259806`

## Public vs `CX36-B (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.715009`
- `CX39-B (Full)`: success_delta_pp=`0.000`, exp_delta=`-9.444`, mean_time_overhead_ratio=`2.720665`
- `CX39-B (No-Compatibility-Witness)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.173839`
- `CX39-B (No-Depth2-Bridge)`: success_delta_pp=`0.000`, exp_delta=`-8.056`, mean_time_overhead_ratio=`1.141046`

## Public Family Breakdown vs `CX36-B (Full)`
- `alpha_puzzle` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.747642`
- `alpha_puzzle` / `CX39-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.507914`
- `alpha_puzzle` / `CX39-B (No-Compatibility-Witness)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.211803`
- `alpha_puzzle` / `CX39-B (No-Depth2-Bridge)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.251217`
- `bug_trap` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.739940`
- `bug_trap` / `CX39-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.330846`
- `bug_trap` / `CX39-B (No-Compatibility-Witness)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.557973`
- `bug_trap` / `CX39-B (No-Depth2-Bridge)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.585903`
- `flange` / `CX3-D`: exp_delta=`-1428.400`, mean_time_overhead_ratio=`-0.698060`
- `flange` / `CX39-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.320017`
- `flange` / `CX39-B (No-Compatibility-Witness)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.951146`
- `flange` / `CX39-B (No-Depth2-Bridge)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.979172`
- `maze` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.817725`
- `maze` / `CX39-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.918979`
- `maze` / `CX39-B (No-Compatibility-Witness)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.976697`
- `maze` / `CX39-B (No-Depth2-Bridge)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.069801`
- `narrow_passage` / `CX3-D`: exp_delta=`-98.250`, mean_time_overhead_ratio=`-0.727616`
- `narrow_passage` / `CX39-B (Full)`: exp_delta=`-42.500`, mean_time_overhead_ratio=`3.519303`
- `narrow_passage` / `CX39-B (No-Compatibility-Witness)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.379869`
- `narrow_passage` / `CX39-B (No-Depth2-Bridge)`: exp_delta=`-36.250`, mean_time_overhead_ratio=`1.488509`
- `parasol_misc` / `CX3-D`: exp_delta=`-12.333`, mean_time_overhead_ratio=`-0.822153`
- `parasol_misc` / `CX39-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.296813`
- `parasol_misc` / `CX39-B (No-Compatibility-Witness)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.317547`
- `parasol_misc` / `CX39-B (No-Depth2-Bridge)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.824672`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`