# CX29-D Pilot V1

- protocol: frozen `CX28-D / Misc Forward-Turn Arbitration` parent; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; no hard-test evidence consumed
- chosen params: `{'maze_revisit_thr': 2, 'maze_stall_steps': 18, 'reverse_required_thr': 0.1, 'trap_thr': 0.54, 'misc_revisit_thr': 1, 'misc_churn_thr': 0.12, 'misc_loop_thr': 0.05, 'block_ttl': 32, 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 32, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24}`
- output root: `outputs/rs_p0cx29_d_pilot_v1`

## Public vs `CX3-D`
- `CX29-D (Full)`: success_delta_pp=`0.000`, exp_delta=`400.722`, mean_time_overhead_ratio=`2.444993`
- `CX29-D (No-Aux-Bridge-Calib)`: success_delta_pp=`0.000`, exp_delta=`399.167`, mean_time_overhead_ratio=`2.433888`

## Public Family Breakdown vs `CX3-D`
- `alpha_puzzle` / `CX29-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.927657`
- `alpha_puzzle` / `CX29-D (No-Aux-Bridge-Calib)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.909505`
- `bug_trap` / `CX29-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.810553`
- `bug_trap` / `CX29-D (No-Aux-Bridge-Calib)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.792329`
- `flange` / `CX29-D (Full)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.283445`
- `flange` / `CX29-D (No-Aux-Bridge-Calib)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.262909`
- `maze` / `CX29-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.726638`
- `maze` / `CX29-D (No-Aux-Bridge-Calib)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.753960`
- `narrow_passage` / `CX29-D (Full)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.644916`
- `narrow_passage` / `CX29-D (No-Aux-Bridge-Calib)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.642636`
- `parasol_misc` / `CX29-D (Full)`: exp_delta=`-53.667`, mean_time_overhead_ratio=`3.616974`
- `parasol_misc` / `CX29-D (No-Aux-Bridge-Calib)`: exp_delta=`-58.333`, mean_time_overhead_ratio=`3.700249`

## Public vs `CX28-D (Full)`
- `CX29-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.167`, mean_time_overhead_ratio=`0.004086`
- `CX29-D (No-Aux-Bridge-Calib)`: success_delta_pp=`0.000`, exp_delta=`-1.389`, mean_time_overhead_ratio=`0.000849`

## Public Family Breakdown vs `CX28-D (Full)`
- `alpha_puzzle` / `CX29-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.006552`
- `alpha_puzzle` / `CX29-D (No-Aux-Bridge-Calib)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.001900`
- `bug_trap` / `CX29-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.008226`
- `bug_trap` / `CX29-D (No-Aux-Bridge-Calib)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.003404`
- `flange` / `CX29-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.003037`
- `flange` / `CX29-D (No-Aux-Bridge-Calib)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.003236`
- `maze` / `CX29-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.000853`
- `maze` / `CX29-D (No-Aux-Bridge-Calib)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.008191`
- `narrow_passage` / `CX29-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.008226`
- `narrow_passage` / `CX29-D (No-Aux-Bridge-Calib)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.007595`
- `parasol_misc` / `CX29-D (Full)`: exp_delta=`0.500`, mean_time_overhead_ratio=`-0.012020`
- `parasol_misc` / `CX29-D (No-Aux-Bridge-Calib)`: exp_delta=`-4.167`, mean_time_overhead_ratio=`0.005800`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
