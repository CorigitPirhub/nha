# CX30-C Pilot V1

- protocol: frozen `CX29-D / Aux-Calibrated Bridge Threshold` parent; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; no hard-test evidence consumed
- chosen params: `{'maze_revisit_thr': 2, 'maze_stall_steps': 18, 'reverse_required_thr': 0.1, 'trap_thr': 0.54, 'bridge_low': 0.1, 'focus_gap_thr': 0.36, 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 32, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24}`
- output root: `outputs/rs_p0cx30_c_pilot_v1`

## Public vs `CX3-D`
- `CX30-C (Full)`: success_delta_pp=`0.000`, exp_delta=`401.444`, mean_time_overhead_ratio=`2.452204`
- `CX30-C (No-LowBridge-Focus)`: success_delta_pp=`0.000`, exp_delta=`399.167`, mean_time_overhead_ratio=`2.453165`

## Public Family Breakdown vs `CX3-D`
- `alpha_puzzle` / `CX30-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.926943`
- `alpha_puzzle` / `CX30-C (No-LowBridge-Focus)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.948085`
- `bug_trap` / `CX30-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.775179`
- `bug_trap` / `CX30-C (No-LowBridge-Focus)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.784622`
- `flange` / `CX30-C (Full)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.300338`
- `flange` / `CX30-C (No-LowBridge-Focus)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.293003`
- `maze` / `CX30-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.738404`
- `maze` / `CX30-C (No-LowBridge-Focus)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.745421`
- `narrow_passage` / `CX30-C (Full)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.643669`
- `narrow_passage` / `CX30-C (No-LowBridge-Focus)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.646925`
- `parasol_misc` / `CX30-C (Full)`: exp_delta=`-51.500`, mean_time_overhead_ratio=`3.519550`
- `parasol_misc` / `CX30-C (No-LowBridge-Focus)`: exp_delta=`-58.333`, mean_time_overhead_ratio=`3.656339`

## Public vs `CX29-D (Full)`
- `CX30-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.722`, mean_time_overhead_ratio=`0.002093`
- `CX30-C (No-LowBridge-Focus)`: success_delta_pp=`0.000`, exp_delta=`-1.556`, mean_time_overhead_ratio=`0.002372`

## Public Family Breakdown vs `CX29-D (Full)`
- `alpha_puzzle` / `CX30-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.000182`
- `alpha_puzzle` / `CX30-C (No-LowBridge-Focus)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.005201`
- `bug_trap` / `CX30-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.009283`
- `bug_trap` / `CX30-C (No-LowBridge-Focus)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.006805`
- `flange` / `CX30-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.005145`
- `flange` / `CX30-C (No-LowBridge-Focus)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.002911`
- `maze` / `CX30-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.003157`
- `maze` / `CX30-C (No-LowBridge-Focus)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.005040`
- `narrow_passage` / `CX30-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.000342`
- `narrow_passage` / `CX30-C (No-LowBridge-Focus)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.000551`
- `parasol_misc` / `CX30-C (Full)`: exp_delta=`2.167`, mean_time_overhead_ratio=`-0.021101`
- `parasol_misc` / `CX30-C (No-LowBridge-Focus)`: exp_delta=`-4.667`, mean_time_overhead_ratio=`0.008526`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
