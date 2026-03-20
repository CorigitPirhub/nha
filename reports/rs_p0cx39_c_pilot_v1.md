# CX39-C Pilot V1

- protocol: frozen `CX36-B / Event-Triggered Compatibility Extension` parent on public evidence; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit
- research anchors:
  - Experience Graphs / reusable local bridge search: https://www.ri.cmu.edu/publications/experience-graphs-leveraging-multiple-planning-graphs-in-motion-planning/
  - Selective reject option / abstain-on-no-advantage: https://proceedings.mlr.press/v97/geifman19a.html
  - Learning model preconditions / initiation-set style gating: https://proceedings.mlr.press/v164/ravichandar22a.html
- chosen params: `{'turn_bridge_max': 0.1, 'turn_focus_max': 0.36, 'rescue_bridge_max': 0.08, 'rescue_focus_min': 0.39, 'rescue_path_min': 0.99, 'rescue_budget': 1, 'suppress_bridge_min': 0.11, 'suppress_bridge_max': 0.13, 'suppress_focus_max': 0.31, 'suppress_path_min': 0.97, 'stubborn_bridge_min': 0.125, 'stubborn_focus_max': 0.34, 'stubborn_path_max': 0.97, 'macro_bridge_min': 0.078, 'macro_bridge_max': 0.095, 'macro_focus_min': 0.34, 'macro_focus_max': 0.37, 'macro_path_min': 0.97, 'macro_path_max': 1.01, 'maze_revisit_thr': 2, 'maze_stall_steps': 18, 'reverse_required_thr': 0.1, 'trap_thr': 0.54, 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 32, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24, 'min_hits': 2, 'max_bridge_depth': 2, 'max_bridge_frontier': 3, 'max_review_targets': 3}`
- output root: `outputs/rs_p0cx39_c_pilot_v1`

## Public vs `CX3-D`
- `CX36-B (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.460739`
- `CX39-B (Full)`: success_delta_pp=`0.000`, exp_delta=`413.278`, mean_time_overhead_ratio=`12.055369`
- `CX39-C (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`19.469019`
- `CX39-C (No-Bridge-Contract)`: success_delta_pp=`0.000`, exp_delta=`413.278`, mean_time_overhead_ratio=`19.441843`
- `CX39-C (No-Depth2-Bridge)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`12.541297`

## Public vs `CX36-B (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.711044`
- `CX39-B (Full)`: success_delta_pp=`0.000`, exp_delta=`-9.444`, mean_time_overhead_ratio=`2.772422`
- `CX39-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`4.914638`
- `CX39-C (No-Bridge-Contract)`: success_delta_pp=`0.000`, exp_delta=`-9.444`, mean_time_overhead_ratio=`4.906785`
- `CX39-C (No-Depth2-Bridge)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`2.912834`

## Public vs `CX39-B (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-413.278`, mean_time_overhead_ratio=`-0.923403`
- `CX36-B (Full)`: success_delta_pp=`0.000`, exp_delta=`9.444`, mean_time_overhead_ratio=`-0.734918`
- `CX39-C (Full)`: success_delta_pp=`0.000`, exp_delta=`9.444`, mean_time_overhead_ratio=`0.567862`
- `CX39-C (No-Bridge-Contract)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.565780`
- `CX39-C (No-Depth2-Bridge)`: success_delta_pp=`0.000`, exp_delta=`9.444`, mean_time_overhead_ratio=`0.037220`

## Public Family Breakdown vs `CX36-B (Full)`
- `alpha_puzzle` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.744266`
- `alpha_puzzle` / `CX39-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.528085`
- `alpha_puzzle` / `CX39-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.931123`
- `alpha_puzzle` / `CX39-C (No-Bridge-Contract)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.926138`
- `alpha_puzzle` / `CX39-C (No-Depth2-Bridge)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.563236`
- `bug_trap` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.735757`
- `bug_trap` / `CX39-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.368338`
- `bug_trap` / `CX39-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.447788`
- `bug_trap` / `CX39-C (No-Bridge-Contract)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.447845`
- `bug_trap` / `CX39-C (No-Depth2-Bridge)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.471259`
- `flange` / `CX3-D`: exp_delta=`-1428.400`, mean_time_overhead_ratio=`-0.694060`
- `flange` / `CX39-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.364007`
- `flange` / `CX39-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.201012`
- `flange` / `CX39-C (No-Bridge-Contract)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.187087`
- `flange` / `CX39-C (No-Depth2-Bridge)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.492827`
- `maze` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.814744`
- `maze` / `CX39-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.983066`
- `maze` / `CX39-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`5.462212`
- `maze` / `CX39-C (No-Bridge-Contract)`: exp_delta=`0.000`, mean_time_overhead_ratio=`5.467208`
- `maze` / `CX39-C (No-Depth2-Bridge)`: exp_delta=`0.000`, mean_time_overhead_ratio=`3.153112`
- `narrow_passage` / `CX3-D`: exp_delta=`-98.250`, mean_time_overhead_ratio=`-0.723476`
- `narrow_passage` / `CX39-B (Full)`: exp_delta=`-42.500`, mean_time_overhead_ratio=`3.587983`
- `narrow_passage` / `CX39-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`6.246441`
- `narrow_passage` / `CX39-C (No-Bridge-Contract)`: exp_delta=`-42.500`, mean_time_overhead_ratio=`6.247143`
- `narrow_passage` / `CX39-C (No-Depth2-Bridge)`: exp_delta=`0.000`, mean_time_overhead_ratio=`3.697214`
- `parasol_misc` / `CX3-D`: exp_delta=`-12.333`, mean_time_overhead_ratio=`-0.819789`
- `parasol_misc` / `CX39-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.340648`
- `parasol_misc` / `CX39-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.724499`
- `parasol_misc` / `CX39-C (No-Bridge-Contract)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.731501`
- `parasol_misc` / `CX39-C (No-Depth2-Bridge)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.801648`

## Public Family Breakdown vs `CX39-B (Full)`
- `alpha_puzzle` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.832644`
- `alpha_puzzle` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.345586`
- `alpha_puzzle` / `CX39-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.263754`
- `alpha_puzzle` / `CX39-C (No-Bridge-Contract)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.260492`
- `alpha_puzzle` / `CX39-C (No-Depth2-Bridge)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.023003`
- `bug_trap` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.888427`
- `bug_trap` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.577763`
- `bug_trap` / `CX39-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.455784`
- `bug_trap` / `CX39-C (No-Bridge-Contract)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.455808`
- `bug_trap` / `CX39-C (No-Depth2-Bridge)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.043457`
- `flange` / `CX3-D`: exp_delta=`-1428.400`, mean_time_overhead_ratio=`-0.909055`
- `flange` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.702735`
- `flange` / `CX39-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.546077`
- `flange` / `CX39-C (No-Bridge-Contract)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.541937`
- `flange` / `CX39-C (No-Depth2-Bridge)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.038294`
- `maze` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.953489`
- `maze` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.748937`
- `maze` / `CX39-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.622421`
- `maze` / `CX39-C (No-Bridge-Contract)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.623676`
- `maze` / `CX39-C (No-Depth2-Bridge)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.042692`
- `narrow_passage` / `CX3-D`: exp_delta=`-55.750`, mean_time_overhead_ratio=`-0.939729`
- `narrow_passage` / `CX36-B (Full)`: exp_delta=`42.500`, mean_time_overhead_ratio=`-0.782039`
- `narrow_passage` / `CX39-C (Full)`: exp_delta=`42.500`, mean_time_overhead_ratio=`0.579439`
- `narrow_passage` / `CX39-C (No-Bridge-Contract)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.579592`
- `narrow_passage` / `CX39-C (No-Depth2-Bridge)`: exp_delta=`42.500`, mean_time_overhead_ratio=`0.023808`
- `parasol_misc` / `CX3-D`: exp_delta=`-12.333`, mean_time_overhead_ratio=`-0.946055`
- `parasol_misc` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.700657`
- `parasol_misc` / `CX39-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.713589`
- `parasol_misc` / `CX39-C (No-Bridge-Contract)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.715685`
- `parasol_misc` / `CX39-C (No-Depth2-Bridge)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.137997`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`