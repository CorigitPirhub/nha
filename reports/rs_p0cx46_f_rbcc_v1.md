# CX46-F Pilot V1

- protocol: unified public rerun against frozen `CX34-A` and `CX41-B`; band-based witness-quality model with sharpened reliable/local reuse contract; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit
- chosen params: `{'review_cell_stride': 3, 'review_yaw_bins': 12, 'margin_thr': 0.03, 'anchor_eps': 0.02, 'enable_parasol_misc': True, 'enable_deadend_labyrinth': True, 'enable_narrow_passage': True, 'band_slack': 0.15, 'similarity_scale': 4.0, 'certainty_floor': 0.2, 'reliable_ttl_boost': 1.05, 'reliable_anchor_boost': 1.0, 'local_ttl_scale': 0.65, 'local_anchor_scale': 0.6, 'max_ttl': 112, 'min_band_count': 8}`
- output root: `outputs/rs_p0cx46_f_rbcc_v1`

## Public vs `CX3-D`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.446282`
- `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`4.209748`
- `CX46-F (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.443076`
- `CX46-F (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.447412`
- `CX46-F (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`378.611`, mean_time_overhead_ratio=`2.417865`

## Public vs `CX34-A (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.709832`
- `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.511701`
- `CX46-F (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.000930`
- `CX46-F (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.000328`
- `CX46-F (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`-44.111`, mean_time_overhead_ratio=`-0.008246`

## Public vs `CX41-B (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.808052`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.338493`
- `CX46-F (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.339109`
- `CX46-F (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.338277`
- `CX46-F (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`-44.111`, mean_time_overhead_ratio=`-0.343948`

## Public Family Breakdown vs `CX34-A (Full)`
- `alpha_puzzle` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.756484`
- `alpha_puzzle` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.569574`
- `alpha_puzzle` / `CX46-F (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.024831`
- `alpha_puzzle` / `CX46-F (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.010790`
- `alpha_puzzle` / `CX46-F (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.007590`
- `bug_trap` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.761016`
- `bug_trap` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.486745`
- `bug_trap` / `CX46-F (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.027302`
- `bug_trap` / `CX46-F (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.012297`
- `bug_trap` / `CX46-F (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.017498`
- `flange` / `CX3-D`: exp_delta=`-1428.400`, mean_time_overhead_ratio=`-0.695975`
- `flange` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.467695`
- `flange` / `CX46-F (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.007033`
- `flange` / `CX46-F (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.002529`
- `flange` / `CX46-F (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.001402`
- `maze` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.739426`
- `maze` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.633500`
- `maze` / `CX46-F (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.003829`
- `maze` / `CX46-F (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.010601`
- `maze` / `CX46-F (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.004183`
- `narrow_passage` / `CX3-D`: exp_delta=`-98.250`, mean_time_overhead_ratio=`-0.728243`
- `narrow_passage` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.507442`
- `narrow_passage` / `CX46-F (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.010288`
- `narrow_passage` / `CX46-F (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.003110`
- `narrow_passage` / `CX46-F (Proxy-Only-Negative)`: exp_delta=`-168.250`, mean_time_overhead_ratio=`-0.015466`
- `parasol_misc` / `CX3-D`: exp_delta=`-12.333`, mean_time_overhead_ratio=`-0.763904`
- `parasol_misc` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.147720`
- `parasol_misc` / `CX46-F (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.001813`
- `parasol_misc` / `CX46-F (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.020657`
- `parasol_misc` / `CX46-F (Proxy-Only-Negative)`: exp_delta=`-20.167`, mean_time_overhead_ratio=`-0.051593`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`