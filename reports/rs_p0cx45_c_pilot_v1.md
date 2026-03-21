# CX45-C Pilot V1

- protocol: unified public rerun against frozen `CX34-A` and `CX41-B`; macro-bearing evidence-accumulated witness; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit
- chosen params: `{'review_cell_stride': 3, 'review_yaw_bins': 12, 'margin_thr': 0.03, 'anchor_eps': 0.02, 'enable_parasol_misc': True, 'enable_deadend_labyrinth': True, 'enable_narrow_passage': True, 'support_thr': 0.6, 'support_decay': 0.9, 'base_ttl': 32, 'ttl_bonus': 64, 'anchor_scale': 1.0, 'margin_scale': 1.0}`
- output root: `outputs/rs_p0cx45_c_pilot_v1`

## Public vs `CX3-D`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.395803`
- `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`4.250565`
- `CX45-C (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.411975`
- `CX45-C (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.419190`
- `CX45-C (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`378.611`, mean_time_overhead_ratio=`2.369690`

## Public vs `CX34-A (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.705519`
- `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.546193`
- `CX45-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.004763`
- `CX45-C (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.006887`
- `CX45-C (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`-44.111`, mean_time_overhead_ratio=`-0.007690`

## Public vs `CX41-B (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.809544`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.353250`
- `CX45-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.350170`
- `CX45-C (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.348796`
- `CX45-C (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`-44.111`, mean_time_overhead_ratio=`-0.358223`

## Public Family Breakdown vs `CX34-A (Full)`
- `alpha_puzzle` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.753372`
- `alpha_puzzle` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.616499`
- `alpha_puzzle` / `CX45-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.005482`
- `alpha_puzzle` / `CX45-C (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.004484`
- `alpha_puzzle` / `CX45-C (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.000502`
- `bug_trap` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.755895`
- `bug_trap` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.601061`
- `bug_trap` / `CX45-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.004677`
- `bug_trap` / `CX45-C (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.005024`
- `bug_trap` / `CX45-C (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.001272`
- `flange` / `CX3-D`: exp_delta=`-1428.400`, mean_time_overhead_ratio=`-0.692089`
- `flange` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.504324`
- `flange` / `CX45-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.002904`
- `flange` / `CX45-C (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.005068`
- `flange` / `CX45-C (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.001880`
- `maze` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.732779`
- `maze` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.693649`
- `maze` / `CX45-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.009633`
- `maze` / `CX45-C (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.000994`
- `maze` / `CX45-C (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.018542`
- `narrow_passage` / `CX3-D`: exp_delta=`-98.250`, mean_time_overhead_ratio=`-0.722625`
- `narrow_passage` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.537672`
- `narrow_passage` / `CX45-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.007062`
- `narrow_passage` / `CX45-C (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.009334`
- `narrow_passage` / `CX45-C (Proxy-Only-Negative)`: exp_delta=`-168.250`, mean_time_overhead_ratio=`-0.017372`
- `parasol_misc` / `CX3-D`: exp_delta=`-12.333`, mean_time_overhead_ratio=`-0.763091`
- `parasol_misc` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.170673`
- `parasol_misc` / `CX45-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.013267`
- `parasol_misc` / `CX45-C (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.014233`
- `parasol_misc` / `CX45-C (Proxy-Only-Negative)`: exp_delta=`-20.167`, mean_time_overhead_ratio=`-0.071024`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`