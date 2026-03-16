# CX28-E Pilot V1

- protocol: frozen `CX27-A / Maze Depression Guard` parent; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; no hard-test evidence consumed
- chosen params: `{'maze_revisit_thr': 2, 'maze_stall_steps': 18, 'reverse_required_thr': 0.1, 'trap_thr': 0.54, 'misc_revisit_thr': 1, 'misc_churn_thr': 0.15, 'misc_loop_thr': 0.06, 'bridge_thr': 0.09, 'switch_margin': 0.01, 'block_ttl': 32, 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 32, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24}`
- output root: `outputs/rs_p0cx28_e_pilot_v1`

## Public vs `CX3-D`
- `CX28-E (Full)`: success_delta_pp=`0.000`, exp_delta=`399.778`, mean_time_overhead_ratio=`2.504000`
- `CX28-E (No-Bridge-Filtered-Turn)`: success_delta_pp=`0.000`, exp_delta=`399.167`, mean_time_overhead_ratio=`2.502079`

## Public Family Breakdown vs `CX3-D`
- `alpha_puzzle` / `CX28-E (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.981033`
- `alpha_puzzle` / `CX28-E (No-Bridge-Filtered-Turn)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.967127`
- `bug_trap` / `CX28-E (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.852352`
- `bug_trap` / `CX28-E (No-Bridge-Filtered-Turn)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.882381`
- `flange` / `CX28-E (Full)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.339984`
- `flange` / `CX28-E (No-Bridge-Filtered-Turn)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.337810`
- `maze` / `CX28-E (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.807097`
- `maze` / `CX28-E (No-Bridge-Filtered-Turn)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.807103`
- `narrow_passage` / `CX28-E (Full)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.702778`
- `narrow_passage` / `CX28-E (No-Bridge-Filtered-Turn)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.700838`
- `parasol_misc` / `CX28-E (Full)`: exp_delta=`-56.500`, mean_time_overhead_ratio=`3.732735`
- `parasol_misc` / `CX28-E (No-Bridge-Filtered-Turn)`: exp_delta=`-58.333`, mean_time_overhead_ratio=`3.735713`

## Public vs `CX27-A (Full)`
- `CX28-E (Full)`: success_delta_pp=`0.000`, exp_delta=`0.611`, mean_time_overhead_ratio=`0.031123`
- `CX28-E (No-Bridge-Filtered-Turn)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.030558`

## Public Family Breakdown vs `CX27-A (Full)`
- `alpha_puzzle` / `CX28-E (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.034091`
- `alpha_puzzle` / `CX28-E (No-Bridge-Filtered-Turn)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.030479`
- `bug_trap` / `CX28-E (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.033896`
- `bug_trap` / `CX28-E (No-Bridge-Filtered-Turn)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.041956`
- `flange` / `CX28-E (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.028943`
- `flange` / `CX28-E (No-Bridge-Filtered-Turn)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.028274`
- `maze` / `CX28-E (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.031605`
- `maze` / `CX28-E (No-Bridge-Filtered-Turn)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.031607`
- `narrow_passage` / `CX28-E (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.030522`
- `narrow_passage` / `CX28-E (No-Bridge-Filtered-Turn)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.029982`
- `parasol_misc` / `CX28-E (Full)`: exp_delta=`1.833`, mean_time_overhead_ratio=`0.066011`
- `parasol_misc` / `CX28-E (No-Bridge-Filtered-Turn)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.066682`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
