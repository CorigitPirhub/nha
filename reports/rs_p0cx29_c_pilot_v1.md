# CX29-C Pilot V1

- protocol: frozen `CX28-D / Misc Forward-Turn Arbitration` parent; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; no hard-test evidence consumed
- chosen params: `{'maze_revisit_thr': 2, 'maze_stall_steps': 18, 'reverse_required_thr': 0.1, 'trap_thr': 0.54, 'misc_revisit_thr': 1, 'misc_churn_thr': 0.15, 'misc_loop_thr': 0.06, 'bridge_thr': 0.1, 'block_ttl': 32, 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 32, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24}`
- output root: `outputs/rs_p0cx29_c_pilot_v1`

## Public vs `CX3-D`
- `CX29-C (Full)`: success_delta_pp=`0.000`, exp_delta=`400.722`, mean_time_overhead_ratio=`1.361321`
- `CX29-C (No-Bridge-Calib)`: success_delta_pp=`0.000`, exp_delta=`399.167`, mean_time_overhead_ratio=`1.358727`

## Public Family Breakdown vs `CX3-D`
- `alpha_puzzle` / `CX29-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.726953`
- `alpha_puzzle` / `CX29-C (No-Bridge-Calib)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.679937`
- `bug_trap` / `CX29-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.617119`
- `bug_trap` / `CX29-C (No-Bridge-Calib)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.581991`
- `flange` / `CX29-C (Full)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`1.255846`
- `flange` / `CX29-C (No-Bridge-Calib)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`1.248498`
- `maze` / `CX29-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.557141`
- `maze` / `CX29-C (No-Bridge-Calib)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.549510`
- `narrow_passage` / `CX29-C (Full)`: exp_delta=`98.250`, mean_time_overhead_ratio=`1.486123`
- `narrow_passage` / `CX29-C (No-Bridge-Calib)`: exp_delta=`98.250`, mean_time_overhead_ratio=`1.489739`
- `parasol_misc` / `CX29-C (Full)`: exp_delta=`-53.667`, mean_time_overhead_ratio=`2.179590`
- `parasol_misc` / `CX29-C (No-Bridge-Calib)`: exp_delta=`-58.333`, mean_time_overhead_ratio=`2.209505`

## Public vs `CX28-D (Full)`
- `CX29-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.167`, mean_time_overhead_ratio=`-0.311764`
- `CX29-C (No-Bridge-Calib)`: success_delta_pp=`0.000`, exp_delta=`-1.389`, mean_time_overhead_ratio=`-0.312520`

## Public Family Breakdown vs `CX28-D (Full)`
- `alpha_puzzle` / `CX29-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.301156`
- `alpha_puzzle` / `CX29-C (No-Bridge-Calib)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.313205`
- `bug_trap` / `CX29-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.307542`
- `bug_trap` / `CX29-C (No-Bridge-Calib)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.316836`
- `flange` / `CX29-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.310877`
- `flange` / `CX29-C (No-Bridge-Calib)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.313121`
- `maze` / `CX29-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.313235`
- `maze` / `CX29-C (No-Bridge-Calib)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.315285`
- `narrow_passage` / `CX29-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.312310`
- `narrow_passage` / `CX29-C (No-Bridge-Calib)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.311309`
- `parasol_misc` / `CX29-C (Full)`: exp_delta=`0.500`, mean_time_overhead_ratio=`-0.319604`
- `parasol_misc` / `CX29-C (No-Bridge-Calib)`: exp_delta=`-4.167`, mean_time_overhead_ratio=`-0.313202`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
