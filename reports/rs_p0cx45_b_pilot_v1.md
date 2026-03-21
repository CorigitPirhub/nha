# CX45-B Pilot V1

- protocol: unified public rerun against frozen `CX34-A` and `CX41-B`; evidence-accumulated witness; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit
- chosen params: `{'review_cell_stride': 3, 'review_yaw_bins': 12, 'margin_thr': 0.03, 'anchor_eps': 0.02, 'enable_parasol_misc': True, 'enable_deadend_labyrinth': True, 'enable_narrow_passage': True, 'support_thr': 0.6, 'support_decay': 0.9, 'base_ttl': 24, 'ttl_bonus': 64, 'anchor_scale': 1.2, 'margin_scale': 1.0}`
- output root: `outputs/rs_p0cx45_b_pilot_v1`

## Public vs `CX3-D`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.434724`
- `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`4.291762`
- `CX45-B (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.477102`
- `CX45-B (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.476342`
- `CX45-B (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`378.611`, mean_time_overhead_ratio=`2.452038`

## Public vs `CX34-A (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.708856`
- `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.540666`
- `CX45-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.012338`
- `CX45-B (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.012117`
- `CX45-B (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`-44.111`, mean_time_overhead_ratio=`0.005041`

## Public vs `CX41-B (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.811027`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.350930`
- `CX45-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.342922`
- `CX45-B (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.343065`
- `CX45-B (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`-44.111`, mean_time_overhead_ratio=`-0.347658`

## Public Family Breakdown vs `CX34-A (Full)`
- `alpha_puzzle` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.746037`
- `alpha_puzzle` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.583722`
- `alpha_puzzle` / `CX45-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.008654`
- `alpha_puzzle` / `CX45-B (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.009442`
- `alpha_puzzle` / `CX45-B (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.039066`
- `bug_trap` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.756114`
- `bug_trap` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.574193`
- `bug_trap` / `CX45-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.015246`
- `bug_trap` / `CX45-B (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.010284`
- `bug_trap` / `CX45-B (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.036368`
- `flange` / `CX3-D`: exp_delta=`-1428.400`, mean_time_overhead_ratio=`-0.695305`
- `flange` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.500655`
- `flange` / `CX45-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.007732`
- `flange` / `CX45-B (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.004520`
- `flange` / `CX45-B (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.013590`
- `maze` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.733909`
- `maze` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.679899`
- `maze` / `CX45-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.001297`
- `maze` / `CX45-B (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.017711`
- `maze` / `CX45-B (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.000116`
- `narrow_passage` / `CX3-D`: exp_delta=`-98.250`, mean_time_overhead_ratio=`-0.726317`
- `narrow_passage` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.530528`
- `narrow_passage` / `CX45-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.018861`
- `narrow_passage` / `CX45-B (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.024129`
- `narrow_passage` / `CX45-B (Proxy-Only-Negative)`: exp_delta=`-168.250`, mean_time_overhead_ratio=`-0.002211`
- `parasol_misc` / `CX3-D`: exp_delta=`-12.333`, mean_time_overhead_ratio=`-0.765133`
- `parasol_misc` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.152002`
- `parasol_misc` / `CX45-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.027866`
- `parasol_misc` / `CX45-B (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.026548`
- `parasol_misc` / `CX45-B (Proxy-Only-Negative)`: exp_delta=`-20.167`, mean_time_overhead_ratio=`-0.061469`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`