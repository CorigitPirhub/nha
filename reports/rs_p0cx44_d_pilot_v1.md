# CX44-D Pilot V1

- protocol: unified public rerun against frozen `CX34-A` and `CX41-B`; softness-weighted redundancy witness; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit
- chosen params: `{'review_cell_stride': 3, 'review_yaw_bins': 12, 'margin_thr': 0.03, 'anchor_eps': 0.02, 'enable_parasol_misc': True, 'enable_deadend_labyrinth': True, 'enable_narrow_passage': True, 'base_ttl': 40, 'ttl_bonus': 72, 'confidence_floor': 0.75, 'anchor_scale': 1.2}`
- output root: `outputs/rs_p0cx44_d_pilot_v1`

## Public vs `CX3-D`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.433965`
- `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`4.408622`
- `CX44-D (Full)`: success_delta_pp=`0.000`, exp_delta=`412.722`, mean_time_overhead_ratio=`3.833694`
- `CX44-D (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`412.722`, mean_time_overhead_ratio=`4.120246`
- `CX44-D (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`368.667`, mean_time_overhead_ratio=`3.995038`

## Public vs `CX34-A (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.708791`
- `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.575037`
- `CX44-D (Full)`: success_delta_pp=`0.000`, exp_delta=`-10.000`, mean_time_overhead_ratio=`0.407613`
- `CX44-D (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`-10.000`, mean_time_overhead_ratio=`0.491059`
- `CX44-D (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`-54.056`, mean_time_overhead_ratio=`0.454598`

## Public vs `CX41-B (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.815110`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.365094`
- `CX44-D (Full)`: success_delta_pp=`0.000`, exp_delta=`-10.000`, mean_time_overhead_ratio=`-0.106299`
- `CX44-D (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`-10.000`, mean_time_overhead_ratio=`-0.053318`
- `CX44-D (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`-54.056`, mean_time_overhead_ratio=`-0.076468`

## Public Family Breakdown vs `CX34-A (Full)`
- `alpha_puzzle` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.759763`
- `alpha_puzzle` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.681796`
- `alpha_puzzle` / `CX44-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.471504`
- `alpha_puzzle` / `CX44-D (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.447988`
- `alpha_puzzle` / `CX44-D (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.462933`
- `bug_trap` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.760531`
- `bug_trap` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.840092`
- `bug_trap` / `CX44-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.516084`
- `bug_trap` / `CX44-D (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.483387`
- `bug_trap` / `CX44-D (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.474283`
- `flange` / `CX3-D`: exp_delta=`-1428.400`, mean_time_overhead_ratio=`-0.694443`
- `flange` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.549714`
- `flange` / `CX44-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.473388`
- `flange` / `CX44-D (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.484202`
- `flange` / `CX44-D (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.462393`
- `maze` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.743032`
- `maze` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.618259`
- `maze` / `CX44-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.049634`
- `maze` / `CX44-D (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.453416`
- `maze` / `CX44-D (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.493872`
- `narrow_passage` / `CX3-D`: exp_delta=`-98.250`, mean_time_overhead_ratio=`-0.727094`
- `narrow_passage` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.541591`
- `narrow_passage` / `CX44-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.330207`
- `narrow_passage` / `CX44-D (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.498609`
- `narrow_passage` / `CX44-D (Proxy-Only-Negative)`: exp_delta=`-168.250`, mean_time_overhead_ratio=`0.445884`
- `parasol_misc` / `CX3-D`: exp_delta=`-12.333`, mean_time_overhead_ratio=`-0.769562`
- `parasol_misc` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.163562`
- `parasol_misc` / `CX44-D (Full)`: exp_delta=`-30.000`, mean_time_overhead_ratio=`0.083696`
- `parasol_misc` / `CX44-D (No-Witness-Transfer)`: exp_delta=`-30.000`, mean_time_overhead_ratio=`0.532533`
- `parasol_misc` / `CX44-D (Proxy-Only-Negative)`: exp_delta=`-50.000`, mean_time_overhead_ratio=`0.408848`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`