# CX46-J Public V1

- protocol: public validation for review-credit scheduler on top of `CX46-F`; candidate selected from dev-summary requiring positive gain vs `CX34-A` and `No-Witness-Transfer` when available
- chosen params: `{'review_cell_stride': 3, 'review_yaw_bins': 12, 'margin_thr': 0.03, 'anchor_eps': 0.02, 'enable_parasol_misc': True, 'enable_deadend_labyrinth': True, 'enable_narrow_passage': True, 'band_slack': 0.15, 'similarity_scale': 4.0, 'certainty_floor': 0.2, 'reliable_ttl_boost': 1.05, 'reliable_anchor_boost': 1.0, 'local_ttl_scale': 0.65, 'local_anchor_scale': 0.6, 'max_ttl': 112, 'min_band_count': 8, 'initial_credit': 3.0, 'miss_cost': 1.0, 'hit_reward': 0.5, 'store_reward': 1.5, 'low_credit_stride': 2, 'min_credit_floor': -3.0}`
- dev choice: `{'trial': 2, 'params': {'review_cell_stride': 3, 'review_yaw_bins': 12, 'margin_thr': 0.03, 'anchor_eps': 0.02, 'enable_parasol_misc': True, 'enable_deadend_labyrinth': True, 'enable_narrow_passage': True, 'band_slack': 0.15, 'similarity_scale': 4.0, 'certainty_floor': 0.2, 'reliable_ttl_boost': 1.05, 'reliable_anchor_boost': 1.0, 'local_ttl_scale': 0.65, 'local_anchor_scale': 0.6, 'max_ttl': 112, 'min_band_count': 8, 'initial_credit': 3.0, 'miss_cost': 1.0, 'hit_reward': 0.5, 'store_reward': 1.5, 'low_credit_stride': 2, 'min_credit_floor': -3.0}, 'time_gain_vs_cx34': 3.6151554169399396, 'time_gain_vs_nowt': 49.21619530900249, 'avg_hits': 28.714285714285715, 'avg_credit_gate_skips': 253.14285714285714}`
- output root: `outputs/rs_p0cx46_j_rrc_public_v1`

## Public vs `CX3-D`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.404364`
- `CX46-F (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.426333`
- `CX46-J (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.419684`
- `CX46-J (No-Credit-Gate)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.431354`
- `CX46-J (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.440925`

## Public vs `CX34-A (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.706259`
- `CX46-F (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.006453`
- `CX46-J (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.004500`
- `CX46-J (No-Credit-Gate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.007928`
- `CX46-J (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.010740`

## Public vs `CX46-F (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.708143`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.006412`
- `CX46-J (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.001941`
- `CX46-J (No-Credit-Gate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.001465`
- `CX46-J (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.004259`

## Public Family Breakdown vs `CX34-A (Full)`
- `alpha_puzzle` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.743718`
- `alpha_puzzle` / `CX46-F (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.011679`
- `alpha_puzzle` / `CX46-J (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.005433`
- `alpha_puzzle` / `CX46-J (No-Credit-Gate)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.014446`
- `alpha_puzzle` / `CX46-J (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.027101`
- `bug_trap` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.740370`
- `bug_trap` / `CX46-F (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.011084`
- `bug_trap` / `CX46-J (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.008379`
- `bug_trap` / `CX46-J (No-Credit-Gate)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.022029`
- `bug_trap` / `CX46-J (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.013399`
- `flange` / `CX3-D`: exp_delta=`-1428.400`, mean_time_overhead_ratio=`-0.693468`
- `flange` / `CX46-F (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.004059`
- `flange` / `CX46-J (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.002823`
- `flange` / `CX46-J (No-Credit-Gate)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.004835`
- `flange` / `CX46-J (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.005302`
- `maze` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.736877`
- `maze` / `CX46-F (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.006912`
- `maze` / `CX46-J (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.003205`
- `maze` / `CX46-J (No-Credit-Gate)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.006537`
- `maze` / `CX46-J (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.012077`
- `narrow_passage` / `CX3-D`: exp_delta=`-98.250`, mean_time_overhead_ratio=`-0.722487`
- `narrow_passage` / `CX46-F (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.011755`
- `narrow_passage` / `CX46-J (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.009386`
- `narrow_passage` / `CX46-J (No-Credit-Gate)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.015025`
- `narrow_passage` / `CX46-J (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.018241`
- `parasol_misc` / `CX3-D`: exp_delta=`-12.333`, mean_time_overhead_ratio=`-0.762395`
- `parasol_misc` / `CX46-F (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.001001`
- `parasol_misc` / `CX46-J (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.010051`
- `parasol_misc` / `CX46-J (No-Credit-Gate)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.003622`
- `parasol_misc` / `CX46-J (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.030299`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`