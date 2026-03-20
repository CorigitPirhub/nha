# CX37-A Pilot V1

- protocol: frozen `CX36-B / Event-Triggered Compatibility Extension` parent on public evidence; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit
- research anchors:
  - DAgger / off-policy data aggregation: Ross et al., AISTATS 2011 — https://proceedings.mlr.press/v15/ross11a/ross11a.pdf
  - Retrospective imitation / search-state replay: https://arxiv.org/abs/1804.00846
  - Model preconditions / structural applicability: Ravichandar et al., CoRL 2021 — https://proceedings.mlr.press/v164/ravichandar22a.html
- chosen params: `{'turn_bridge_max': 0.1, 'turn_focus_max': 0.36, 'rescue_bridge_max': 0.08, 'rescue_focus_min': 0.39, 'rescue_path_min': 0.99, 'rescue_budget': 1, 'suppress_bridge_min': 0.11, 'suppress_bridge_max': 0.13, 'suppress_focus_max': 0.31, 'suppress_path_min': 0.97, 'stubborn_bridge_min': 0.125, 'stubborn_focus_max': 0.34, 'stubborn_path_max': 0.97, 'macro_bridge_min': 0.078, 'macro_bridge_max': 0.095, 'macro_focus_min': 0.34, 'macro_focus_max': 0.37, 'macro_path_min': 0.97, 'macro_path_max': 1.01, 'maze_revisit_thr': 2, 'maze_stall_steps': 18, 'reverse_required_thr': 0.1, 'trap_thr': 0.54, 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 32, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24, 'min_hits': 2}`
- output root: `outputs/rs_p0cx37_a_pilot_v1`

## Public vs `CX3-D`
- `CX36-B (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.508376`
- `CX37-A (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.509557`
- `CX37-A (No-Replay-Contract)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.512604`
- `CX37-A (No-Replay-Trigger)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.439397`

## Public Family Breakdown vs `CX3-D`
- `alpha_puzzle` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`3.019760`
- `alpha_puzzle` / `CX37-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.952065`
- `alpha_puzzle` / `CX37-A (No-Replay-Contract)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.930797`
- `alpha_puzzle` / `CX37-A (No-Replay-Trigger)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.896871`
- `bug_trap` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.874491`
- `bug_trap` / `CX37-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.824159`
- `bug_trap` / `CX37-A (No-Replay-Contract)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.825063`
- `bug_trap` / `CX37-A (No-Replay-Trigger)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.773783`
- `flange` / `CX36-B (Full)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.323028`
- `flange` / `CX37-A (Full)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.314791`
- `flange` / `CX37-A (No-Replay-Contract)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.315989`
- `flange` / `CX37-A (No-Replay-Trigger)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.280763`
- `maze` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.437788`
- `maze` / `CX37-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.463816`
- `maze` / `CX37-A (No-Replay-Contract)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.466056`
- `maze` / `CX37-A (No-Replay-Trigger)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.755386`
- `narrow_passage` / `CX36-B (Full)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.650562`
- `narrow_passage` / `CX37-A (Full)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.667578`
- `narrow_passage` / `CX37-A (No-Replay-Contract)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.673779`
- `narrow_passage` / `CX37-A (No-Replay-Trigger)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.640641`
- `parasol_misc` / `CX36-B (Full)`: exp_delta=`12.333`, mean_time_overhead_ratio=`4.593877`
- `parasol_misc` / `CX37-A (Full)`: exp_delta=`12.333`, mean_time_overhead_ratio=`4.624276`
- `parasol_misc` / `CX37-A (No-Replay-Contract)`: exp_delta=`12.333`, mean_time_overhead_ratio=`4.632966`
- `parasol_misc` / `CX37-A (No-Replay-Trigger)`: exp_delta=`12.333`, mean_time_overhead_ratio=`3.541919`

## Public vs `CX36-B (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.714968`
- `CX37-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.000337`
- `CX37-A (No-Replay-Contract)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.001205`
- `CX37-A (No-Replay-Trigger)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.019661`

## Public Family Breakdown vs `CX36-B (Full)`
- `alpha_puzzle` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.751229`
- `alpha_puzzle` / `CX37-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.016840`
- `alpha_puzzle` / `CX37-A (No-Replay-Contract)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.022131`
- `alpha_puzzle` / `CX37-A (No-Replay-Trigger)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.030571`
- `bug_trap` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.741902`
- `bug_trap` / `CX37-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.012991`
- `bug_trap` / `CX37-A (No-Replay-Contract)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.012757`
- `bug_trap` / `CX37-A (No-Replay-Trigger)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.025992`
- `flange` / `CX3-D`: exp_delta=`-1428.400`, mean_time_overhead_ratio=`-0.699070`
- `flange` / `CX37-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.002479`
- `flange` / `CX37-A (No-Replay-Contract)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.002118`
- `flange` / `CX37-A (No-Replay-Trigger)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.012719`
- `maze` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.816102`
- `maze` / `CX37-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.004787`
- `maze` / `CX37-A (No-Replay-Contract)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.005198`
- `maze` / `CX37-A (No-Replay-Trigger)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.309391`
- `narrow_passage` / `CX3-D`: exp_delta=`-98.250`, mean_time_overhead_ratio=`-0.726070`
- `narrow_passage` / `CX37-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.004661`
- `narrow_passage` / `CX37-A (No-Replay-Contract)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.006360`
- `narrow_passage` / `CX37-A (No-Replay-Trigger)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.002718`
- `parasol_misc` / `CX3-D`: exp_delta=`-12.333`, mean_time_overhead_ratio=`-0.821233`
- `parasol_misc` / `CX37-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.005434`
- `parasol_misc` / `CX37-A (No-Replay-Contract)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.006988`
- `parasol_misc` / `CX37-A (No-Replay-Trigger)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.188055`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`