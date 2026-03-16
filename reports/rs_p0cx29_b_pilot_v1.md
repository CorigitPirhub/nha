# CX29-B Pilot V1

- protocol: frozen `CX28-D / Misc Forward-Turn Arbitration` parent; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; no hard-test evidence consumed
- chosen params: `{'maze_revisit_thr': 2, 'maze_stall_steps': 18, 'reverse_required_thr': 0.1, 'trap_thr': 0.54, 'misc_revisit_thr': 1, 'misc_churn_thr': 0.15, 'misc_loop_thr': 0.06, 'switch_margin': 0.0, 'block_ttl': 32, 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 32, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24, 'straight_share': 1}`
- output root: `outputs/rs_p0cx29_b_pilot_v1`

## Public vs `CX3-D`
- `CX29-B (Full)`: success_delta_pp=`0.000`, exp_delta=`400.222`, mean_time_overhead_ratio=`1.320480`
- `CX29-B (No-ForwardTurn-Blend)`: success_delta_pp=`0.000`, exp_delta=`399.167`, mean_time_overhead_ratio=`1.316586`

## Public Family Breakdown vs `CX3-D`
- `alpha_puzzle` / `CX29-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.572579`
- `alpha_puzzle` / `CX29-B (No-ForwardTurn-Blend)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.636065`
- `bug_trap` / `CX29-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.487713`
- `bug_trap` / `CX29-B (No-ForwardTurn-Blend)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.483531`
- `flange` / `CX29-B (Full)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`1.210991`
- `flange` / `CX29-B (No-ForwardTurn-Blend)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`1.210736`
- `maze` / `CX29-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.513317`
- `maze` / `CX29-B (No-ForwardTurn-Blend)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.453584`
- `narrow_passage` / `CX29-B (Full)`: exp_delta=`98.250`, mean_time_overhead_ratio=`1.454592`
- `narrow_passage` / `CX29-B (No-ForwardTurn-Blend)`: exp_delta=`98.250`, mean_time_overhead_ratio=`1.442021`
- `parasol_misc` / `CX29-B (Full)`: exp_delta=`-55.167`, mean_time_overhead_ratio=`2.128368`
- `parasol_misc` / `CX29-B (No-ForwardTurn-Blend)`: exp_delta=`-58.333`, mean_time_overhead_ratio=`2.139482`

## Public vs `CX28-D (Full)`
- `CX29-B (Full)`: success_delta_pp=`0.000`, exp_delta=`-0.333`, mean_time_overhead_ratio=`-0.323667`
- `CX29-B (No-ForwardTurn-Blend)`: success_delta_pp=`0.000`, exp_delta=`-1.389`, mean_time_overhead_ratio=`-0.324802`

## Public Family Breakdown vs `CX28-D (Full)`
- `alpha_puzzle` / `CX29-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.340718`
- `alpha_puzzle` / `CX29-B (No-ForwardTurn-Blend)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.324448`
- `bug_trap` / `CX29-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.341781`
- `bug_trap` / `CX29-B (No-ForwardTurn-Blend)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.342888`
- `flange` / `CX29-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.324579`
- `flange` / `CX29-B (No-ForwardTurn-Blend)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.324657`
- `maze` / `CX29-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.325005`
- `maze` / `CX29-B (No-ForwardTurn-Blend)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.341048`
- `narrow_passage` / `CX29-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.321031`
- `narrow_passage` / `CX29-B (No-ForwardTurn-Blend)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.324509`
- `parasol_misc` / `CX29-B (Full)`: exp_delta=`-1.000`, mean_time_overhead_ratio=`-0.330565`
- `parasol_misc` / `CX29-B (No-ForwardTurn-Blend)`: exp_delta=`-4.167`, mean_time_overhead_ratio=`-0.328186`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
