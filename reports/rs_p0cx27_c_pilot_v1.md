# CX27-C Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; this round stayed public-first and did not consume hard-test evidence
- chosen params: `{'revisit_thr': 2, 'stall_steps': 14, 'churn_thr': 0.4, 'loop_thr': 0.1, 'reverse_required_thr': 0.08, 'trap_thr': 0.5, 'failure_thr': 1, 'progress_eps': 0.02, 'commit_fail_margin': 0.04, 'failure_ttl': 32, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24}`
- output root: `outputs/rs_p0cx27_c_pilot_v1`

## Public vs `CX3-D`
- `CX27-C (Full)`: success_delta_pp=`0.000`, exp_delta=`384.778`, mean_time_overhead_ratio=`2.535617`
- `CX27-C (No-Failure-Memory)`: success_delta_pp=`0.000`, exp_delta=`392.889`, mean_time_overhead_ratio=`2.557030`

## Public Family Breakdown vs `CX3-D`
- `alpha_puzzle` / `CX27-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.978980`
- `alpha_puzzle` / `CX27-C (No-Failure-Memory)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.974754`
- `bug_trap` / `CX27-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.775847`
- `bug_trap` / `CX27-C (No-Failure-Memory)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.894025`
- `flange` / `CX27-C (Full)`: exp_delta=`1377.400`, mean_time_overhead_ratio=`2.371527`
- `flange` / `CX27-C (No-Failure-Memory)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.396322`
- `maze` / `CX27-C (Full)`: exp_delta=`-3.000`, mean_time_overhead_ratio=`2.794382`
- `maze` / `CX27-C (No-Failure-Memory)`: exp_delta=`-113.000`, mean_time_overhead_ratio=`6.065929`
- `narrow_passage` / `CX27-C (Full)`: exp_delta=`98.000`, mean_time_overhead_ratio=`2.755263`
- `narrow_passage` / `CX27-C (No-Failure-Memory)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.752579`
- `parasol_misc` / `CX27-C (Full)`: exp_delta=`-58.333`, mean_time_overhead_ratio=`3.571674`
- `parasol_misc` / `CX27-C (No-Failure-Memory)`: exp_delta=`-58.333`, mean_time_overhead_ratio=`3.590694`

## Public vs `CX23-C (Full)`
- `CX27-C (Full)`: success_delta_pp=`0.000`, exp_delta=`-8.111`, mean_time_overhead_ratio=`0.498371`
- `CX27-C (No-Failure-Memory)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.507446`

## Public Family Breakdown vs `CX23-C (Full)`
- `alpha_puzzle` / `CX27-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.493242`
- `alpha_puzzle` / `CX27-C (No-Failure-Memory)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.491656`
- `bug_trap` / `CX27-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.482348`
- `bug_trap` / `CX27-C (No-Failure-Memory)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.528743`
- `flange` / `CX27-C (Full)`: exp_delta=`-51.000`, mean_time_overhead_ratio=`0.497557`
- `flange` / `CX27-C (No-Failure-Memory)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.508570`
- `maze` / `CX27-C (Full)`: exp_delta=`110.000`, mean_time_overhead_ratio=`-0.197760`
- `maze` / `CX27-C (No-Failure-Memory)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.493938`
- `narrow_passage` / `CX27-C (Full)`: exp_delta=`-0.250`, mean_time_overhead_ratio=`0.508818`
- `narrow_passage` / `CX27-C (No-Failure-Memory)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.507739`
- `parasol_misc` / `CX27-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.484480`
- `parasol_misc` / `CX27-C (No-Failure-Memory)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.490656`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`