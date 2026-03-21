# CX45-A Pilot V1

- protocol: unified public rerun against frozen `CX34-A` and `CX41-B`; quality-calibrated witness transfer; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit
- chosen params: `{'review_cell_stride': 3, 'review_yaw_bins': 12, 'margin_thr': 0.03, 'anchor_eps': 0.02, 'enable_parasol_misc': True, 'enable_deadend_labyrinth': True, 'enable_narrow_passage': True, 'conf_thr': 0.78, 'base_ttl': 24, 'ttl_bonus': 48, 'anchor_scale': 1.2, 'margin_scale': 1.0}`
- output root: `outputs/rs_p0cx45_a_pilot_v1`

## Public vs `CX3-D`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.356257`
- `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`4.091774`
- `CX45-A (Full)`: success_delta_pp=`0.000`, exp_delta=`412.722`, mean_time_overhead_ratio=`2.369089`
- `CX45-A (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`412.722`, mean_time_overhead_ratio=`2.352133`
- `CX45-A (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`368.667`, mean_time_overhead_ratio=`2.384968`

## Public vs `CX34-A (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.702049`
- `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.517099`
- `CX45-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-10.000`, mean_time_overhead_ratio=`0.003823`
- `CX45-A (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`-10.000`, mean_time_overhead_ratio=`-0.001229`
- `CX45-A (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`-54.056`, mean_time_overhead_ratio=`0.008555`

## Public vs `CX41-B (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.803605`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.340847`
- `CX45-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-10.000`, mean_time_overhead_ratio=`-0.338327`
- `CX45-A (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`-10.000`, mean_time_overhead_ratio=`-0.341657`
- `CX45-A (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`-54.056`, mean_time_overhead_ratio=`-0.335208`

## Public Family Breakdown vs `CX34-A (Full)`
- `alpha_puzzle` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.756894`
- `alpha_puzzle` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.541963`
- `alpha_puzzle` / `CX45-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.002436`
- `alpha_puzzle` / `CX45-A (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.004978`
- `alpha_puzzle` / `CX45-A (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.013250`
- `bug_trap` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.752472`
- `bug_trap` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.521166`
- `bug_trap` / `CX45-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.024479`
- `bug_trap` / `CX45-A (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.036680`
- `bug_trap` / `CX45-A (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.012309`
- `flange` / `CX3-D`: exp_delta=`-1428.400`, mean_time_overhead_ratio=`-0.687473`
- `flange` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.484116`
- `flange` / `CX45-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.003118`
- `flange` / `CX45-A (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.001859`
- `flange` / `CX45-A (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.017065`
- `maze` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.736908`
- `maze` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.602768`
- `maze` / `CX45-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.002343`
- `maze` / `CX45-A (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.014303`
- `maze` / `CX45-A (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.015945`
- `narrow_passage` / `CX3-D`: exp_delta=`-98.250`, mean_time_overhead_ratio=`-0.720938`
- `narrow_passage` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.496400`
- `narrow_passage` / `CX45-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.011772`
- `narrow_passage` / `CX45-A (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.002791`
- `narrow_passage` / `CX45-A (Proxy-Only-Negative)`: exp_delta=`-168.250`, mean_time_overhead_ratio=`-0.001660`
- `parasol_misc` / `CX3-D`: exp_delta=`-12.333`, mean_time_overhead_ratio=`-0.760630`
- `parasol_misc` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.117647`
- `parasol_misc` / `CX45-A (Full)`: exp_delta=`-30.000`, mean_time_overhead_ratio=`0.041177`
- `parasol_misc` / `CX45-A (No-Witness-Transfer)`: exp_delta=`-30.000`, mean_time_overhead_ratio=`0.021198`
- `parasol_misc` / `CX45-A (Proxy-Only-Negative)`: exp_delta=`-50.000`, mean_time_overhead_ratio=`-0.032185`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`