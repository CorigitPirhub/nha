# CX46-D Pilot V1

- protocol: unified public rerun against frozen `CX34-A` and `CX41-B`; witness-quality representation with `reliable/local/fragile` negative-witness bands; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit
- chosen params: `{'review_cell_stride': 3, 'review_yaw_bins': 12, 'margin_thr': 0.03, 'anchor_eps': 0.02, 'enable_parasol_misc': True, 'enable_deadend_labyrinth': True, 'enable_narrow_passage': True, 'band_slack': 0.15, 'similarity_scale': 4.0, 'reliable_weight': 1.3, 'local_weight': 0.45, 'fragile_weight': 0.9, 'anchor_gain': 1.25, 'ttl_gain': 0.9, 'max_ttl': 112, 'min_band_count': 8}`
- output root: `outputs/rs_p0cx46_d_wqr_v1`

## Public vs `CX3-D`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.382800`
- `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`4.165068`
- `CX46-D (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.386114`
- `CX46-D (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.400654`
- `CX46-D (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`378.611`, mean_time_overhead_ratio=`2.355268`

## Public vs `CX34-A (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.704387`
- `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.526862`
- `CX46-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.000980`
- `CX46-D (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.005278`
- `CX46-D (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`-44.111`, mean_time_overhead_ratio=`-0.008139`

## Public vs `CX41-B (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.806392`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.345062`
- `CX46-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.344420`
- `CX46-D (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.341605`
- `CX46-D (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`-44.111`, mean_time_overhead_ratio=`-0.350392`

## Public Family Breakdown vs `CX34-A (Full)`
- `alpha_puzzle` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.747679`
- `alpha_puzzle` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.613631`
- `alpha_puzzle` / `CX46-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.005119`
- `alpha_puzzle` / `CX46-D (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.004695`
- `alpha_puzzle` / `CX46-D (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.000145`
- `bug_trap` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.751386`
- `bug_trap` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.579556`
- `bug_trap` / `CX46-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.011661`
- `bug_trap` / `CX46-D (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.006551`
- `bug_trap` / `CX46-D (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.005306`
- `flange` / `CX3-D`: exp_delta=`-1428.400`, mean_time_overhead_ratio=`-0.690145`
- `flange` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.486681`
- `flange` / `CX46-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.001183`
- `flange` / `CX46-D (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.002165`
- `flange` / `CX46-D (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.002547`
- `maze` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.737411`
- `maze` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.661430`
- `maze` / `CX46-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.004607`
- `maze` / `CX46-D (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.001438`
- `maze` / `CX46-D (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.000884`
- `narrow_passage` / `CX3-D`: exp_delta=`-98.250`, mean_time_overhead_ratio=`-0.723080`
- `narrow_passage` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.517224`
- `narrow_passage` / `CX46-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.002034`
- `narrow_passage` / `CX46-D (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.009139`
- `narrow_passage` / `CX46-D (Proxy-Only-Negative)`: exp_delta=`-168.250`, mean_time_overhead_ratio=`-0.019242`
- `parasol_misc` / `CX3-D`: exp_delta=`-12.333`, mean_time_overhead_ratio=`-0.760883`
- `parasol_misc` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.142588`
- `parasol_misc` / `CX46-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.010729`
- `parasol_misc` / `CX46-D (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.020013`
- `parasol_misc` / `CX46-D (Proxy-Only-Negative)`: exp_delta=`-20.167`, mean_time_overhead_ratio=`-0.075971`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`