# CX32-A Pilot V1

- protocol: frozen `CX30-C / Low-Bridge + Focus Gate` parent; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; no hard-test evidence consumed
- chosen params: `{'maze_revisit_thr': 2, 'maze_stall_steps': 18, 'reverse_required_thr': 0.1, 'trap_thr': 0.54, 'turn_bridge_max': 0.1, 'turn_focus_max': 0.36, 'rescue_bridge_max': 0.08, 'rescue_focus_min': 0.39, 'rescue_path_min': 0.99, 'rescue_target': 'reverse_setup|reverse', 'suppress_bridge_min': 0.11, 'suppress_bridge_max': 0.13, 'suppress_focus_max': 0.31, 'suppress_path_min': 0.97, 'suppress_target': 'uncertain|none', 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 32, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24}`
- output root: `outputs/rs_p0cx32_a_pilot_v1`

## Public vs `CX3-D`
- `CX32-A (Full)`: success_delta_pp=`0.000`, exp_delta=`404.389`, mean_time_overhead_ratio=`2.470546`
- `CX32-A (No-Dual-Slice-Repair)`: success_delta_pp=`0.000`, exp_delta=`399.167`, mean_time_overhead_ratio=`2.481067`

## Public Family Breakdown vs `CX3-D`
- `alpha_puzzle` / `CX32-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.880369`
- `alpha_puzzle` / `CX32-A (No-Dual-Slice-Repair)`: exp_delta=`0.000`, mean_time_overhead_ratio=`3.015814`
- `bug_trap` / `CX32-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.760237`
- `bug_trap` / `CX32-A (No-Dual-Slice-Repair)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.814357`
- `flange` / `CX32-A (Full)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.311041`
- `flange` / `CX32-A (No-Dual-Slice-Repair)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.322078`
- `maze` / `CX32-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.789186`
- `maze` / `CX32-A (No-Dual-Slice-Repair)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.769077`
- `narrow_passage` / `CX32-A (Full)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.672273`
- `narrow_passage` / `CX32-A (No-Dual-Slice-Repair)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.673153`
- `parasol_misc` / `CX32-A (Full)`: exp_delta=`-42.667`, mean_time_overhead_ratio=`3.585316`
- `parasol_misc` / `CX32-A (No-Dual-Slice-Repair)`: exp_delta=`-58.333`, mean_time_overhead_ratio=`3.677679`

## Public vs `CX30-C (Full)`
- `CX32-A (Full)`: success_delta_pp=`0.000`, exp_delta=`2.944`, mean_time_overhead_ratio=`0.005313`
- `CX32-A (No-Dual-Slice-Repair)`: success_delta_pp=`0.000`, exp_delta=`-2.278`, mean_time_overhead_ratio=`0.008361`

## Public Family Breakdown vs `CX30-C (Full)`
- `alpha_puzzle` / `CX32-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.011860`
- `alpha_puzzle` / `CX32-A (No-Dual-Slice-Repair)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.022631`
- `bug_trap` / `CX32-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.003958`
- `bug_trap` / `CX32-A (No-Dual-Slice-Repair)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.010378`
- `flange` / `CX32-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.003243`
- `flange` / `CX32-A (No-Dual-Slice-Repair)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.006587`
- `maze` / `CX32-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.013584`
- `maze` / `CX32-A (No-Dual-Slice-Repair)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.008205`
- `narrow_passage` / `CX32-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.007850`
- `narrow_passage` / `CX32-A (No-Dual-Slice-Repair)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.008092`
- `parasol_misc` / `CX32-A (Full)`: exp_delta=`8.833`, mean_time_overhead_ratio=`0.014551`
- `parasol_misc` / `CX32-A (No-Dual-Slice-Repair)`: exp_delta=`-6.833`, mean_time_overhead_ratio=`0.034988`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
