# CX39-A Pilot V1

- protocol: frozen `CX36-B / Event-Triggered Compatibility Extension` parent on public evidence; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit
- research anchors:
  - Prioritized sweeping / review scheduling: https://proceedings.neurips.cc/paper_files/paper/1992/file/55743cc0393b1cb4b8b37d09ae48d097-Paper.pdf
  - DAgger / off-policy data aggregation: https://proceedings.mlr.press/v15/ross11a/ross11a.pdf
  - Retrospective imitation / replay: https://arxiv.org/abs/1804.00846
- chosen params: `{'turn_bridge_max': 0.1, 'turn_focus_max': 0.36, 'rescue_bridge_max': 0.08, 'rescue_focus_min': 0.39, 'rescue_path_min': 0.99, 'rescue_budget': 1, 'suppress_bridge_min': 0.11, 'suppress_bridge_max': 0.13, 'suppress_focus_max': 0.31, 'suppress_path_min': 0.97, 'stubborn_bridge_min': 0.125, 'stubborn_focus_max': 0.34, 'stubborn_path_max': 0.97, 'macro_bridge_min': 0.078, 'macro_bridge_max': 0.095, 'macro_focus_min': 0.34, 'macro_focus_max': 0.37, 'macro_path_min': 0.97, 'macro_path_max': 1.01, 'maze_revisit_thr': 2, 'maze_stall_steps': 18, 'reverse_required_thr': 0.1, 'trap_thr': 0.54, 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 32, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24, 'min_hits': 2, 'max_review_targets': 2}`
- output root: `outputs/rs_p0cx39_a_pilot_v1`

## Public vs `CX3-D`
- `CX36-B (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.544792`
- `CX39-A (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`5.979142`
- `CX39-A (No-Detour-Generator)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.569402`
- `CX39-A (No-Review-Prior)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`5.900397`

## Public Family Breakdown vs `CX3-D`
- `alpha_puzzle` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`3.011828`
- `alpha_puzzle` / `CX39-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`3.830885`
- `alpha_puzzle` / `CX39-A (No-Detour-Generator)`: exp_delta=`0.000`, mean_time_overhead_ratio=`3.079713`
- `alpha_puzzle` / `CX39-A (No-Review-Prior)`: exp_delta=`0.000`, mean_time_overhead_ratio=`3.753173`
- `bug_trap` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.876485`
- `bug_trap` / `CX39-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.934245`
- `bug_trap` / `CX39-A (No-Detour-Generator)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.966847`
- `bug_trap` / `CX39-A (No-Review-Prior)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.877048`
- `flange` / `CX36-B (Full)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.342477`
- `flange` / `CX39-A (Full)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`5.203298`
- `flange` / `CX39-A (No-Detour-Generator)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.374914`
- `flange` / `CX39-A (No-Review-Prior)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`5.137230`
- `maze` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.473149`
- `maze` / `CX39-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`27.256600`
- `maze` / `CX39-A (No-Detour-Generator)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.567610`
- `maze` / `CX39-A (No-Review-Prior)`: exp_delta=`0.000`, mean_time_overhead_ratio=`27.039669`
- `narrow_passage` / `CX36-B (Full)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.712844`
- `narrow_passage` / `CX39-A (Full)`: exp_delta=`98.250`, mean_time_overhead_ratio=`7.334740`
- `narrow_passage` / `CX39-A (No-Detour-Generator)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.727520`
- `narrow_passage` / `CX39-A (No-Review-Prior)`: exp_delta=`98.250`, mean_time_overhead_ratio=`7.231930`
- `parasol_misc` / `CX36-B (Full)`: exp_delta=`12.333`, mean_time_overhead_ratio=`4.709754`
- `parasol_misc` / `CX39-A (Full)`: exp_delta=`12.333`, mean_time_overhead_ratio=`6.897952`
- `parasol_misc` / `CX39-A (No-Detour-Generator)`: exp_delta=`12.333`, mean_time_overhead_ratio=`4.675092`
- `parasol_misc` / `CX39-A (No-Review-Prior)`: exp_delta=`12.333`, mean_time_overhead_ratio=`6.811767`

## Public vs `CX36-B (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.717896`
- `CX39-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.968844`
- `CX39-A (No-Detour-Generator)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.006942`
- `CX39-A (No-Review-Prior)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.946630`

## Public Family Breakdown vs `CX36-B (Full)`
- `alpha_puzzle` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.750737`
- `alpha_puzzle` / `CX39-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.204161`
- `alpha_puzzle` / `CX39-A (No-Detour-Generator)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.016921`
- `alpha_puzzle` / `CX39-A (No-Review-Prior)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.184790`
- `bug_trap` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.742034`
- `bug_trap` / `CX39-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.530831`
- `bug_trap` / `CX39-A (No-Detour-Generator)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.023310`
- `bug_trap` / `CX39-A (No-Review-Prior)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.516076`
- `flange` / `CX3-D`: exp_delta=`-1428.400`, mean_time_overhead_ratio=`-0.700821`
- `flange` / `CX39-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.855898`
- `flange` / `CX39-A (No-Detour-Generator)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.009705`
- `flange` / `CX39-A (No-Review-Prior)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.836132`
- `maze` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.817290`
- `maze` / `CX39-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.162769`
- `maze` / `CX39-A (No-Detour-Generator)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.017259`
- `maze` / `CX39-A (No-Review-Prior)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.123133`
- `narrow_passage` / `CX3-D`: exp_delta=`-98.250`, mean_time_overhead_ratio=`-0.730665`
- `narrow_passage` / `CX39-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.244840`
- `narrow_passage` / `CX39-A (No-Detour-Generator)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.003953`
- `narrow_passage` / `CX39-A (No-Review-Prior)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.217149`
- `parasol_misc` / `CX3-D`: exp_delta=`-12.333`, mean_time_overhead_ratio=`-0.824861`
- `parasol_misc` / `CX39-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.383239`
- `parasol_misc` / `CX39-A (No-Detour-Generator)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.006071`
- `parasol_misc` / `CX39-A (No-Review-Prior)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.368144`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`