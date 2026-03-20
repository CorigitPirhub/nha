# CX40-D Pilot V1

- protocol: frozen `CX40-A / Contract-Distilled Selective Bridge Cascade` parent on public evidence; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit
- research anchors:
  - Experience Graphs / reusable local bridge search: https://www.ri.cmu.edu/publications/experience-graphs-leveraging-multiple-planning-graphs-in-motion-planning/
  - LazySP / deferred expensive edge evaluation: https://arxiv.org/abs/1707.04015
  - SelectiveNet / selective expensive-evaluation abstention: https://proceedings.mlr.press/v97/geifman19a.html
- chosen params: `{'turn_bridge_max': 0.1, 'turn_focus_max': 0.36, 'rescue_bridge_max': 0.08, 'rescue_focus_min': 0.39, 'rescue_path_min': 0.99, 'rescue_budget': 1, 'suppress_bridge_min': 0.11, 'suppress_bridge_max': 0.13, 'suppress_focus_max': 0.31, 'suppress_path_min': 0.97, 'stubborn_bridge_min': 0.125, 'stubborn_focus_max': 0.34, 'stubborn_path_max': 0.97, 'macro_bridge_min': 0.078, 'macro_bridge_max': 0.095, 'macro_focus_min': 0.34, 'macro_focus_max': 0.37, 'macro_path_min': 0.97, 'macro_path_max': 1.01, 'maze_revisit_thr': 2, 'maze_stall_steps': 18, 'reverse_required_thr': 0.1, 'trap_thr': 0.54, 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 32, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24, 'min_hits': 2, 'max_bridge_depth': 2, 'max_bridge_frontier': 3, 'max_review_targets': 3, 'max_screened_paths': 2, 'seed_min_hits': 2}`
- output root: `outputs/rs_p0cx40_d_pilot_v1`

## Public vs `CX40-A (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.899192`
- `CX36-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.759768`
- `CX39-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.063447`
- `CX40-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.349179`
- `CX40-D (No-Online-Refinement)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.373505`
- `CX40-D (No-Seed-Bank)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.349076`

## Public Family Breakdown vs `CX40-A (Full)`
- `alpha_puzzle` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.770828`
- `alpha_puzzle` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.384829`
- `alpha_puzzle` / `CX39-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.730548`
- `alpha_puzzle` / `CX40-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.554667`
- `alpha_puzzle` / `CX40-D (No-Online-Refinement)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.028844`
- `alpha_puzzle` / `CX40-D (No-Seed-Bank)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.547855`
- `bug_trap` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.852152`
- `bug_trap` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.615229`
- `bug_trap` / `CX39-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.929084`
- `bug_trap` / `CX40-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.509920`
- `bug_trap` / `CX40-D (No-Online-Refinement)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.049325`
- `bug_trap` / `CX40-D (No-Seed-Bank)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.494738`
- `flange` / `CX3-D`: exp_delta=`-1428.400`, mean_time_overhead_ratio=`-0.880668`
- `flange` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.731138`
- `flange` / `CX39-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.028653`
- `flange` / `CX40-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.346385`
- `flange` / `CX40-D (No-Online-Refinement)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.272120`
- `flange` / `CX40-D (No-Seed-Bank)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.345525`
- `maze` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.938605`
- `maze` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.770303`
- `maze` / `CX39-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.141627`
- `maze` / `CX40-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.537856`
- `maze` / `CX40-D (No-Online-Refinement)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.532265`
- `maze` / `CX40-D (No-Seed-Bank)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.537187`
- `narrow_passage` / `CX3-D`: exp_delta=`-98.250`, mean_time_overhead_ratio=`-0.919192`
- `narrow_passage` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.799651`
- `narrow_passage` / `CX39-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.117615`
- `narrow_passage` / `CX40-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.325492`
- `narrow_passage` / `CX40-D (No-Online-Refinement)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.489172`
- `narrow_passage` / `CX40-D (No-Seed-Bank)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.325932`
- `parasol_misc` / `CX3-D`: exp_delta=`-12.333`, mean_time_overhead_ratio=`-0.936686`
- `parasol_misc` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.754423`
- `parasol_misc` / `CX39-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.011194`
- `parasol_misc` / `CX40-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.542020`
- `parasol_misc` / `CX40-D (No-Online-Refinement)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.535399`
- `parasol_misc` / `CX40-D (No-Seed-Bank)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.545625`

## Public vs `CX39-C (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.951146`
- `CX36-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.883577`
- `CX40-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.515374`
- `CX40-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.346153`
- `CX40-D (No-Online-Refinement)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.334364`
- `CX40-D (No-Seed-Bank)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.346202`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`