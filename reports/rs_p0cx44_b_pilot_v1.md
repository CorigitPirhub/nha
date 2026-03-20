# CX44-B Pilot V1

- protocol: unified public rerun against frozen `CX34-A` and `CX41-B`; family-conditional witness transfer on `parasol_misc / deadend_labyrinth / narrow_passage`; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit
- chosen params: `{'review_cell_stride': 3, 'review_yaw_bins': 12, 'margin_thr': 0.03, 'anchor_eps': 0.02, 'enable_parasol_misc': True, 'enable_deadend_labyrinth': True, 'enable_narrow_passage': True}`
- output root: `outputs/rs_p0cx44_b_pilot_v1`

## Public vs `CX3-D`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.310845`
- `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`4.059179`
- `CX44-B (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.310059`
- `CX44-B (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.299127`
- `CX44-B (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`378.611`, mean_time_overhead_ratio=`2.263473`

## Public vs `CX34-A (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.697962`
- `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.528063`
- `CX44-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.000237`
- `CX44-B (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.003539`
- `CX44-B (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`-44.111`, mean_time_overhead_ratio=`-0.014308`

## Public vs `CX41-B (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.802339`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.345577`
- `CX44-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.345732`
- `CX44-B (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.347893`
- `CX44-B (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`-44.111`, mean_time_overhead_ratio=`-0.354940`

## Public Family Breakdown vs `CX34-A (Full)`
- `alpha_puzzle` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.747557`
- `alpha_puzzle` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.599062`
- `alpha_puzzle` / `CX44-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.002772`
- `alpha_puzzle` / `CX44-B (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.010426`
- `alpha_puzzle` / `CX44-B (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.000700`
- `bug_trap` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.749003`
- `bug_trap` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.558005`
- `bug_trap` / `CX44-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.011971`
- `bug_trap` / `CX44-B (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.004062`
- `bug_trap` / `CX44-B (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.001348`
- `flange` / `CX3-D`: exp_delta=`-1428.400`, mean_time_overhead_ratio=`-0.683704`
- `flange` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.490608`
- `flange` / `CX44-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.002765`
- `flange` / `CX44-B (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.004770`
- `flange` / `CX44-B (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.003542`
- `maze` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.726287`
- `maze` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.645733`
- `maze` / `CX44-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.005854`
- `maze` / `CX44-B (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.005794`
- `maze` / `CX44-B (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.003912`
- `narrow_passage` / `CX3-D`: exp_delta=`-98.250`, mean_time_overhead_ratio=`-0.715996`
- `narrow_passage` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.514717`
- `narrow_passage` / `CX44-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.001562`
- `narrow_passage` / `CX44-B (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.001806`
- `narrow_passage` / `CX44-B (Proxy-Only-Negative)`: exp_delta=`-168.250`, mean_time_overhead_ratio=`-0.022370`
- `parasol_misc` / `CX3-D`: exp_delta=`-12.333`, mean_time_overhead_ratio=`-0.758867`
- `parasol_misc` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.130973`
- `parasol_misc` / `CX44-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.033670`
- `parasol_misc` / `CX44-B (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.000064`
- `parasol_misc` / `CX44-B (Proxy-Only-Negative)`: exp_delta=`-20.167`, mean_time_overhead_ratio=`-0.106942`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`