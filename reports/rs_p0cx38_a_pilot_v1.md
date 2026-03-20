# CX38-A Pilot V1

- protocol: frozen `CX36-B / Event-Triggered Compatibility Extension` parent on public evidence; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit
- research anchors:
  - Prioritized sweeping / review scheduling: https://proceedings.neurips.cc/paper_files/paper/1992/file/55743cc0393b1cb4b8b37d09ae48d097-Paper.pdf
  - DAgger / off-policy data aggregation: https://proceedings.mlr.press/v15/ross11a/ross11a.pdf
  - Retrospective imitation / replay: https://arxiv.org/abs/1804.00846
- chosen params: `{'turn_bridge_max': 0.1, 'turn_focus_max': 0.36, 'rescue_bridge_max': 0.08, 'rescue_focus_min': 0.39, 'rescue_path_min': 0.99, 'rescue_budget': 1, 'suppress_bridge_min': 0.11, 'suppress_bridge_max': 0.13, 'suppress_focus_max': 0.31, 'suppress_path_min': 0.97, 'stubborn_bridge_min': 0.125, 'stubborn_focus_max': 0.34, 'stubborn_path_max': 0.97, 'macro_bridge_min': 0.078, 'macro_bridge_max': 0.095, 'macro_focus_min': 0.34, 'macro_focus_max': 0.37, 'macro_path_min': 0.97, 'macro_path_max': 1.01, 'maze_revisit_thr': 2, 'maze_stall_steps': 18, 'reverse_required_thr': 0.1, 'trap_thr': 0.54, 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 32, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24, 'min_hits': 2}`
- output root: `outputs/rs_p0cx38_a_pilot_v1`

## Public vs `CX3-D`
- `CX36-B (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`1.527335`
- `CX38-A (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`1.536057`
- `CX38-A (No-Bounded-Review)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`1.558922`
- `CX38-A (No-Replay-Activation)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`1.509215`

## Public Family Breakdown vs `CX3-D`
- `alpha_puzzle` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.901143`
- `alpha_puzzle` / `CX38-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.868643`
- `alpha_puzzle` / `CX38-A (No-Bounded-Review)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.843408`
- `alpha_puzzle` / `CX38-A (No-Replay-Activation)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.812057`
- `bug_trap` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.750044`
- `bug_trap` / `CX38-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.766738`
- `bug_trap` / `CX38-A (No-Bounded-Review)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.775461`
- `bug_trap` / `CX38-A (No-Replay-Activation)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.737311`
- `flange` / `CX36-B (Full)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`1.382605`
- `flange` / `CX38-A (Full)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`1.399430`
- `flange` / `CX38-A (No-Bounded-Review)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`1.424552`
- `flange` / `CX38-A (No-Replay-Activation)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`1.394128`
- `maze` / `CX36-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`3.005488`
- `maze` / `CX38-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.994539`
- `maze` / `CX38-A (No-Bounded-Review)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.961701`
- `maze` / `CX38-A (No-Replay-Activation)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.692766`
- `narrow_passage` / `CX36-B (Full)`: exp_delta=`98.250`, mean_time_overhead_ratio=`1.638013`
- `narrow_passage` / `CX38-A (Full)`: exp_delta=`98.250`, mean_time_overhead_ratio=`1.633136`
- `narrow_passage` / `CX38-A (No-Bounded-Review)`: exp_delta=`98.250`, mean_time_overhead_ratio=`1.655442`
- `narrow_passage` / `CX38-A (No-Replay-Activation)`: exp_delta=`98.250`, mean_time_overhead_ratio=`1.650418`
- `parasol_misc` / `CX36-B (Full)`: exp_delta=`12.333`, mean_time_overhead_ratio=`3.160836`
- `parasol_misc` / `CX38-A (Full)`: exp_delta=`12.333`, mean_time_overhead_ratio=`3.144774`
- `parasol_misc` / `CX38-A (No-Bounded-Review)`: exp_delta=`12.333`, mean_time_overhead_ratio=`3.133090`
- `parasol_misc` / `CX38-A (No-Replay-Activation)`: exp_delta=`12.333`, mean_time_overhead_ratio=`2.356848`

## Public vs `CX36-B (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.604326`
- `CX38-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.003451`
- `CX38-A (No-Bounded-Review)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.012498`
- `CX38-A (No-Replay-Activation)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.007169`

## Public Family Breakdown vs `CX36-B (Full)`
- `alpha_puzzle` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.655308`
- `alpha_puzzle` / `CX38-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.011202`
- `alpha_puzzle` / `CX38-A (No-Bounded-Review)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.019901`
- `alpha_puzzle` / `CX38-A (No-Replay-Activation)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.030707`
- `bug_trap` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.636369`
- `bug_trap` / `CX38-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.006070`
- `bug_trap` / `CX38-A (No-Bounded-Review)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.009242`
- `bug_trap` / `CX38-A (No-Replay-Activation)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.004630`
- `flange` / `CX3-D`: exp_delta=`-1428.400`, mean_time_overhead_ratio=`-0.580291`
- `flange` / `CX38-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.007062`
- `flange` / `CX38-A (No-Bounded-Review)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.017605`
- `flange` / `CX38-A (No-Replay-Activation)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.004836`
- `maze` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.750343`
- `maze` / `CX38-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.002734`
- `maze` / `CX38-A (No-Bounded-Review)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.010932`
- `maze` / `CX38-A (No-Replay-Activation)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.327731`
- `narrow_passage` / `CX3-D`: exp_delta=`-98.250`, mean_time_overhead_ratio=`-0.620927`
- `narrow_passage` / `CX38-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.001849`
- `narrow_passage` / `CX38-A (No-Bounded-Review)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.006607`
- `narrow_passage` / `CX38-A (No-Replay-Activation)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.004702`
- `parasol_misc` / `CX3-D`: exp_delta=`-12.333`, mean_time_overhead_ratio=`-0.759664`
- `parasol_misc` / `CX38-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.003860`
- `parasol_misc` / `CX38-A (No-Bounded-Review)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.006668`
- `parasol_misc` / `CX38-A (No-Replay-Activation)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.193228`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`