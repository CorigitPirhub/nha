# CX46-C Pilot V1

- protocol: unified public rerun against frozen `CX34-A` and `CX41-B`; scenario-calibrated macro-bearing witness prior; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit
- chosen params: `{'review_cell_stride': 3, 'review_yaw_bins': 12, 'margin_thr': 0.03, 'anchor_eps': 0.02, 'enable_parasol_misc': True, 'enable_deadend_labyrinth': True, 'enable_narrow_passage': True, 'misc_prior_floor': 0.88, 'deadend_prior_floor': 0.45, 'narrow_prior_floor': 0.3, 'misc_support_thr': 0.92, 'deadend_support_thr': 0.55, 'narrow_support_thr': 0.45, 'support_decay': 0.9, 'base_ttl': 24, 'ttl_bonus': 64, 'anchor_scale': 1.0}`
- output root: `outputs/rs_p0cx46_c_pilot_v1`

## Public vs `CX3-D`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.400108`
- `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`4.283927`
- `CX46-C (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.463398`
- `CX46-C (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.421363`
- `CX46-C (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.428746`

## Public vs `CX34-A (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.705892`
- `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.554047`
- `CX46-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.018614`
- `CX46-C (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.006251`
- `CX46-C (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.008423`

## Public vs `CX41-B (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.810747`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.356519`
- `CX46-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.344541`
- `CX46-C (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.352496`
- `CX46-C (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.351099`

## Public Family Breakdown vs `CX34-A (Full)`
- `alpha_puzzle` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.751336`
- `alpha_puzzle` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.576829`
- `alpha_puzzle` / `CX46-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.000041`
- `alpha_puzzle` / `CX46-C (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.029696`
- `alpha_puzzle` / `CX46-C (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.000431`
- `bug_trap` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.750977`
- `bug_trap` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.513294`
- `bug_trap` / `CX46-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.036142`
- `bug_trap` / `CX46-C (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.034155`
- `bug_trap` / `CX46-C (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.017522`
- `flange` / `CX3-D`: exp_delta=`-1428.400`, mean_time_overhead_ratio=`-0.692544`
- `flange` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.518585`
- `flange` / `CX46-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.014163`
- `flange` / `CX46-C (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.003544`
- `flange` / `CX46-C (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.006728`
- `maze` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.735923`
- `maze` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.658960`
- `maze` / `CX46-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.017285`
- `maze` / `CX46-C (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.000265`
- `maze` / `CX46-C (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.008481`
- `narrow_passage` / `CX3-D`: exp_delta=`-98.250`, mean_time_overhead_ratio=`-0.722087`
- `narrow_passage` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.538872`
- `narrow_passage` / `CX46-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.027469`
- `narrow_passage` / `CX46-C (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.011543`
- `narrow_passage` / `CX46-C (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.010893`
- `parasol_misc` / `CX3-D`: exp_delta=`-12.333`, mean_time_overhead_ratio=`-0.769950`
- `parasol_misc` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.138555`
- `parasol_misc` / `CX46-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.013312`
- `parasol_misc` / `CX46-C (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.004251`
- `parasol_misc` / `CX46-C (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.013585`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`