# CX37-B Pilot V1

- protocol: frozen `CX36-B / Event-Triggered Compatibility Extension` parent on public evidence; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit
- research anchors:
  - DAgger / off-policy data aggregation: Ross et al., AISTATS 2011 — https://proceedings.mlr.press/v15/ross11a/ross11a.pdf
  - Retrospective imitation / search-state replay: https://arxiv.org/abs/1804.00846
  - Model preconditions / structural applicability: Ravichandar et al., CoRL 2021 — https://proceedings.mlr.press/v164/ravichandar22a.html
- chosen params: `{'turn_bridge_max': 0.1, 'turn_focus_max': 0.36, 'rescue_bridge_max': 0.08, 'rescue_focus_min': 0.39, 'rescue_path_min': 0.99, 'rescue_budget': 1, 'suppress_bridge_min': 0.11, 'suppress_bridge_max': 0.13, 'suppress_focus_max': 0.31, 'suppress_path_min': 0.97, 'stubborn_bridge_min': 0.125, 'stubborn_focus_max': 0.34, 'stubborn_path_max': 0.97, 'macro_bridge_min': 0.078, 'macro_bridge_max': 0.095, 'macro_focus_min': 0.34, 'macro_focus_max': 0.37, 'macro_path_min': 0.97, 'macro_path_max': 1.01, 'maze_revisit_thr': 2, 'maze_stall_steps': 18, 'reverse_required_thr': 0.1, 'trap_thr': 0.54, 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 32, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24, 'min_hits': 2}`
- output root: `outputs/rs_p0cx37_rerun_v2/rs_p0cx37_b_pilot_v1`

## Public vs `CX3-D`
- `CX36-B (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.475327`
- `CX37-B (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.526984`
- `CX37-B (No-Replay-Prior)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.541402`
- `CX37-B (No-Replay-Scheduler)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.442860`

## Public Family Breakdown vs `CX3-D`
- `alpha_puzzle` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.918317`
- `alpha_puzzle` / `CX37-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.947740`
- `alpha_puzzle` / `CX37-B (No-Replay-Prior)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.977317`
- `alpha_puzzle` / `CX37-B (No-Replay-Scheduler)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.946481`
- `bug_trap` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.806947`
- `bug_trap` / `CX37-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.838724`
- `bug_trap` / `CX37-B (No-Replay-Prior)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.892756`
- `bug_trap` / `CX37-B (No-Replay-Scheduler)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.817325`
- `flange` / `CX36-B (Full)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.280506`
- `flange` / `CX37-B (Full)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.345622`
- `flange` / `CX37-B (No-Replay-Prior)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.337419`
- `flange` / `CX37-B (No-Replay-Scheduler)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.305669`
- `maze` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.453712`
- `maze` / `CX37-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.466815`
- `maze` / `CX37-B (No-Replay-Prior)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.481808`
- `maze` / `CX37-B (No-Replay-Scheduler)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.705625`
- `narrow_passage` / `CX36-B (Full)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.634501`
- `narrow_passage` / `CX37-B (Full)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.658667`
- `narrow_passage` / `CX37-B (No-Replay-Prior)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.712053`
- `narrow_passage` / `CX37-B (No-Replay-Scheduler)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.607353`
- `parasol_misc` / `CX36-B (Full)`: exp_delta=`12.333`, mean_time_overhead_ratio=`4.578948`
- `parasol_misc` / `CX37-B (Full)`: exp_delta=`12.333`, mean_time_overhead_ratio=`4.635757`
- `parasol_misc` / `CX37-B (No-Replay-Prior)`: exp_delta=`12.333`, mean_time_overhead_ratio=`4.713143`
- `parasol_misc` / `CX37-B (No-Replay-Scheduler)`: exp_delta=`12.333`, mean_time_overhead_ratio=`3.486110`

## Public vs `CX36-B (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.712257`
- `CX37-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.014864`
- `CX37-B (No-Replay-Prior)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.019013`
- `CX37-B (No-Replay-Scheduler)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.009342`

## Public Family Breakdown vs `CX36-B (Full)`
- `alpha_puzzle` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.744788`
- `alpha_puzzle` / `CX37-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.007509`
- `alpha_puzzle` / `CX37-B (No-Replay-Prior)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.015058`
- `alpha_puzzle` / `CX37-B (No-Replay-Scheduler)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.007188`
- `bug_trap` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.737322`
- `bug_trap` / `CX37-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.008347`
- `bug_trap` / `CX37-B (No-Replay-Prior)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.022540`
- `bug_trap` / `CX37-B (No-Replay-Scheduler)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.002726`
- `flange` / `CX3-D`: exp_delta=`-1428.400`, mean_time_overhead_ratio=`-0.695169`
- `flange` / `CX37-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.019849`
- `flange` / `CX37-B (No-Replay-Prior)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.017349`
- `flange` / `CX37-B (No-Replay-Scheduler)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.007671`
- `maze` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.816639`
- `maze` / `CX37-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.002403`
- `maze` / `CX37-B (No-Replay-Prior)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.005152`
- `maze` / `CX37-B (No-Replay-Scheduler)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.320532`
- `narrow_passage` / `CX3-D`: exp_delta=`-98.250`, mean_time_overhead_ratio=`-0.724859`
- `narrow_passage` / `CX37-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.006649`
- `narrow_passage` / `CX37-B (No-Replay-Prior)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.021338`
- `narrow_passage` / `CX37-B (No-Replay-Scheduler)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.007470`
- `parasol_misc` / `CX3-D`: exp_delta=`-12.333`, mean_time_overhead_ratio=`-0.820755`
- `parasol_misc` / `CX37-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.010183`
- `parasol_misc` / `CX37-B (No-Replay-Prior)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.024054`
- `parasol_misc` / `CX37-B (No-Replay-Scheduler)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.195886`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`