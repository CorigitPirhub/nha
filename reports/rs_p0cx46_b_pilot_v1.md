# CX46-B Pilot V1

- protocol: unified public rerun against frozen `CX34-A` and `CX41-B`; scenario-calibrated witness prior; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit
- chosen params: `{'review_cell_stride': 3, 'review_yaw_bins': 12, 'margin_thr': 0.03, 'anchor_eps': 0.02, 'enable_parasol_misc': True, 'enable_deadend_labyrinth': True, 'enable_narrow_passage': True, 'misc_prior_floor': 0.92, 'deadend_prior_floor': 0.55, 'narrow_prior_floor': 0.45, 'misc_support_thr': 0.95, 'deadend_support_thr': 0.6, 'narrow_support_thr': 0.55, 'support_decay': 0.9, 'base_ttl': 24, 'ttl_bonus': 64, 'anchor_scale': 1.0}`
- output root: `outputs/rs_p0cx46_b_pilot_v1`

## Public vs `CX3-D`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.446415`
- `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`4.269773`
- `CX46-B (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.434797`
- `CX46-B (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.443026`
- `CX46-B (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.440597`

## Public vs `CX34-A (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.709843`
- `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.529060`
- `CX46-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.003371`
- `CX46-B (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.000983`
- `CX46-B (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.001688`

## Public vs `CX41-B (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.810239`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.346003`
- `CX46-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.348208`
- `CX46-B (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.346646`
- `CX46-B (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.347107`

## Public Family Breakdown vs `CX34-A (Full)`
- `alpha_puzzle` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.751327`
- `alpha_puzzle` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.591411`
- `alpha_puzzle` / `CX46-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.027768`
- `alpha_puzzle` / `CX46-B (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.030123`
- `alpha_puzzle` / `CX46-B (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.027026`
- `bug_trap` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.753611`
- `bug_trap` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.527872`
- `bug_trap` / `CX46-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.008851`
- `bug_trap` / `CX46-B (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.026727`
- `bug_trap` / `CX46-B (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.030709`
- `flange` / `CX3-D`: exp_delta=`-1428.400`, mean_time_overhead_ratio=`-0.696543`
- `flange` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.481649`
- `flange` / `CX46-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.007958`
- `flange` / `CX46-B (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.004625`
- `flange` / `CX46-B (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.005241`
- `maze` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.741747`
- `maze` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.665947`
- `maze` / `CX46-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.006613`
- `maze` / `CX46-B (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.009091`
- `maze` / `CX46-B (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.006811`
- `narrow_passage` / `CX3-D`: exp_delta=`-98.250`, mean_time_overhead_ratio=`-0.726451`
- `narrow_passage` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.534713`
- `narrow_passage` / `CX46-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.004579`
- `narrow_passage` / `CX46-B (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.005146`
- `narrow_passage` / `CX46-B (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.004403`
- `parasol_misc` / `CX3-D`: exp_delta=`-12.333`, mean_time_overhead_ratio=`-0.770319`
- `parasol_misc` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.123910`
- `parasol_misc` / `CX46-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.000704`
- `parasol_misc` / `CX46-B (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.003251`
- `parasol_misc` / `CX46-B (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.001790`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`