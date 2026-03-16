# CX29-A Pilot V1

- protocol: frozen `CX28-D / Misc Forward-Turn Arbitration` parent; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; no hard-test evidence consumed
- chosen params: `{'maze_revisit_thr': 2, 'maze_stall_steps': 18, 'reverse_required_thr': 0.1, 'trap_thr': 0.54, 'misc_revisit_thr': 1, 'misc_churn_thr': 0.12, 'misc_loop_thr': 0.05, 'rollout_depth': 3, 'rollout_discount': 0.8, 'switch_margin': 0.0, 'abstain_margin': -0.01, 'block_ttl': 32, 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 32, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24}`
- output root: `outputs/rs_p0cx29_a_pilot_v1`

## Public vs `CX3-D`
- `CX29-A (Full)`: success_delta_pp=`0.000`, exp_delta=`399.167`, mean_time_overhead_ratio=`1.403115`
- `CX29-A (No-Rollout-Review)`: success_delta_pp=`0.000`, exp_delta=`399.167`, mean_time_overhead_ratio=`1.390117`

## Public Family Breakdown vs `CX3-D`
- `alpha_puzzle` / `CX29-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.768602`
- `alpha_puzzle` / `CX29-A (No-Rollout-Review)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.692347`
- `bug_trap` / `CX29-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.727996`
- `bug_trap` / `CX29-A (No-Rollout-Review)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.592923`
- `flange` / `CX29-A (Full)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`1.282654`
- `flange` / `CX29-A (No-Rollout-Review)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`1.276855`
- `maze` / `CX29-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.612429`
- `maze` / `CX29-A (No-Rollout-Review)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.605181`
- `narrow_passage` / `CX29-A (Full)`: exp_delta=`98.250`, mean_time_overhead_ratio=`1.530671`
- `narrow_passage` / `CX29-A (No-Rollout-Review)`: exp_delta=`98.250`, mean_time_overhead_ratio=`1.522185`
- `parasol_misc` / `CX29-A (Full)`: exp_delta=`-58.333`, mean_time_overhead_ratio=`2.479821`
- `parasol_misc` / `CX29-A (No-Rollout-Review)`: exp_delta=`-58.333`, mean_time_overhead_ratio=`2.287595`

## Public vs `CX28-D (Full)`
- `CX29-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-1.389`, mean_time_overhead_ratio=`-0.299582`
- `CX29-A (No-Rollout-Review)`: success_delta_pp=`0.000`, exp_delta=`-1.389`, mean_time_overhead_ratio=`-0.303371`

## Public Family Breakdown vs `CX28-D (Full)`
- `alpha_puzzle` / `CX29-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.290483`
- `alpha_puzzle` / `CX29-A (No-Rollout-Review)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.310025`
- `bug_trap` / `CX29-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.278205`
- `bug_trap` / `CX29-A (No-Rollout-Review)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.313944`
- `flange` / `CX29-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.302687`
- `flange` / `CX29-A (No-Rollout-Review)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.304459`
- `maze` / `CX29-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.298387`
- `maze` / `CX29-A (No-Rollout-Review)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.300333`
- `narrow_passage` / `CX29-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.299987`
- `narrow_passage` / `CX29-A (No-Rollout-Review)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.302334`
- `parasol_misc` / `CX29-A (Full)`: exp_delta=`-4.167`, mean_time_overhead_ratio=`-0.255358`
- `parasol_misc` / `CX29-A (No-Rollout-Review)`: exp_delta=`-4.167`, mean_time_overhead_ratio=`-0.296492`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
