# CX34-A Pilot V1

- protocol: frozen `CX33-B / Budgeted Stubborn-Slice Repair` parent; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; no hard-test evidence consumed
- chosen params: `{'turn_bridge_max': 0.1, 'turn_focus_max': 0.36, 'rescue_bridge_max': 0.08, 'rescue_focus_min': 0.39, 'rescue_path_min': 0.99, 'rescue_budget': 1, 'suppress_bridge_min': 0.11, 'suppress_bridge_max': 0.13, 'suppress_focus_max': 0.31, 'suppress_path_min': 0.97, 'stubborn_bridge_min': 0.125, 'stubborn_focus_max': 0.34, 'stubborn_path_max': 0.97, 'macro_bridge_min': 0.078, 'macro_bridge_max': 0.095, 'macro_focus_min': 0.34, 'macro_focus_max': 0.37, 'macro_path_min': 0.97, 'macro_path_max': 1.01, 'maze_revisit_thr': 2, 'maze_stall_steps': 18, 'reverse_required_thr': 0.1, 'trap_thr': 0.54, 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 32, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24}`
- output root: `outputs/rs_p0cx34_a_pilot_v1`

## Public vs `CX3-D`
- `CX33-B (Full)`: success_delta_pp=`0.000`, exp_delta=`411.444`, mean_time_overhead_ratio=`3.504408`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`420.389`, mean_time_overhead_ratio=`3.527234`
- `CX34-A (No-Custom-Macro-Rescue)`: success_delta_pp=`0.000`, exp_delta=`411.444`, mean_time_overhead_ratio=`3.529359`

## Public Family Breakdown vs `CX3-D`
- `alpha_puzzle` / `CX33-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.328395`
- `alpha_puzzle` / `CX34-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.323819`
- `alpha_puzzle` / `CX34-A (No-Custom-Macro-Rescue)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.323563`
- `bug_trap` / `CX33-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.192765`
- `bug_trap` / `CX34-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.307586`
- `bug_trap` / `CX34-A (No-Custom-Macro-Rescue)`: exp_delta=`0.000`, mean_time_overhead_ratio=`4.191066`
- `flange` / `CX33-B (Full)`: exp_delta=`1421.000`, mean_time_overhead_ratio=`3.312233`
- `flange` / `CX34-A (Full)`: exp_delta=`1421.000`, mean_time_overhead_ratio=`3.336465`
- `flange` / `CX34-A (No-Custom-Macro-Rescue)`: exp_delta=`1421.000`, mean_time_overhead_ratio=`3.334269`
- `maze` / `CX33-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`3.872242`
- `maze` / `CX34-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`3.914200`
- `maze` / `CX34-A (No-Custom-Macro-Rescue)`: exp_delta=`0.000`, mean_time_overhead_ratio=`3.904300`
- `narrow_passage` / `CX33-B (Full)`: exp_delta=`99.750`, mean_time_overhead_ratio=`3.761150`
- `narrow_passage` / `CX34-A (Full)`: exp_delta=`99.750`, mean_time_overhead_ratio=`3.789361`
- `narrow_passage` / `CX34-A (No-Custom-Macro-Rescue)`: exp_delta=`99.750`, mean_time_overhead_ratio=`3.784813`
- `parasol_misc` / `CX33-B (Full)`: exp_delta=`-16.333`, mean_time_overhead_ratio=`4.716537`
- `parasol_misc` / `CX34-A (Full)`: exp_delta=`10.500`, mean_time_overhead_ratio=`4.660825`
- `parasol_misc` / `CX34-A (No-Custom-Macro-Rescue)`: exp_delta=`-16.333`, mean_time_overhead_ratio=`4.809005`

## Public vs `CX33-B (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-411.444`, mean_time_overhead_ratio=`-0.777995`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`8.944`, mean_time_overhead_ratio=`0.005068`
- `CX34-A (No-Custom-Macro-Rescue)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.005539`

## Public Family Breakdown vs `CX33-B (Full)`
- `alpha_puzzle` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.812326`
- `alpha_puzzle` / `CX34-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.000859`
- `alpha_puzzle` / `CX34-A (No-Custom-Macro-Rescue)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.000907`
- `bug_trap` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.807424`
- `bug_trap` / `CX34-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.022112`
- `bug_trap` / `CX34-A (No-Custom-Macro-Rescue)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.000327`
- `flange` / `CX3-D`: exp_delta=`-1421.000`, mean_time_overhead_ratio=`-0.768102`
- `flange` / `CX34-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.005619`
- `flange` / `CX34-A (No-Custom-Macro-Rescue)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.005110`
- `maze` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.794756`
- `maze` / `CX34-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.008612`
- `maze` / `CX34-A (No-Custom-Macro-Rescue)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.006580`
- `narrow_passage` / `CX3-D`: exp_delta=`-99.750`, mean_time_overhead_ratio=`-0.789967`
- `narrow_passage` / `CX34-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.005925`
- `narrow_passage` / `CX34-A (No-Custom-Macro-Rescue)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.004970`
- `parasol_misc` / `CX3-D`: exp_delta=`16.333`, mean_time_overhead_ratio=`-0.825069`
- `parasol_misc` / `CX34-A (Full)`: exp_delta=`26.833`, mean_time_overhead_ratio=`-0.009746`
- `parasol_misc` / `CX34-A (No-Custom-Macro-Rescue)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.016176`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
