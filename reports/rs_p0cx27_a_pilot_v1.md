# CX27-A Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; this round stayed public-first and did not consume hard-test evidence
- chosen params: `{'revisit_thr': 2, 'stall_steps': 18, 'reverse_required_thr': 0.1, 'trap_thr': 0.54, 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 40, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24}`
- output root: `outputs/rs_p0cx27_a_pilot_v1`

## Public vs `CX3-D`
- `CX27-A (Full)`: success_delta_pp=`0.000`, exp_delta=`399.167`, mean_time_overhead_ratio=`2.398235`
- `CX27-A (No-Maze-Guard)`: success_delta_pp=`0.000`, exp_delta=`392.889`, mean_time_overhead_ratio=`2.409031`

## Public Family Breakdown vs `CX3-D`
- `alpha_puzzle` / `CX27-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.849791`
- `alpha_puzzle` / `CX27-A (No-Maze-Guard)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.843887`
- `bug_trap` / `CX27-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.726052`
- `bug_trap` / `CX27-A (No-Maze-Guard)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.749179`
- `flange` / `CX27-A (Full)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.246033`
- `flange` / `CX27-A (No-Maze-Guard)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.249324`
- `maze` / `CX27-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.690460`
- `maze` / `CX27-A (No-Maze-Guard)`: exp_delta=`-113.000`, mean_time_overhead_ratio=`6.039369`
- `narrow_passage` / `CX27-A (Full)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.593107`
- `narrow_passage` / `CX27-A (No-Maze-Guard)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.601872`
- `parasol_misc` / `CX27-A (Full)`: exp_delta=`-58.333`, mean_time_overhead_ratio=`3.439668`
- `parasol_misc` / `CX27-A (No-Maze-Guard)`: exp_delta=`-58.333`, mean_time_overhead_ratio=`3.442896`

## Public vs `CX23-C (Full)`
- `CX27-A (Full)`: success_delta_pp=`0.000`, exp_delta=`6.278`, mean_time_overhead_ratio=`0.440150`
- `CX27-A (No-Maze-Guard)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.444725`

## Public Family Breakdown vs `CX23-C (Full)`
- `alpha_puzzle` / `CX27-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.444760`
- `alpha_puzzle` / `CX27-A (No-Maze-Guard)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.442544`
- `bug_trap` / `CX27-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.462800`
- `bug_trap` / `CX27-A (No-Maze-Guard)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.471879`
- `flange` / `CX27-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.441815`
- `flange` / `CX27-A (No-Maze-Guard)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.443277`
- `maze` / `CX27-A (Full)`: exp_delta=`113.000`, mean_time_overhead_ratio=`-0.219732`
- `maze` / `CX27-A (No-Maze-Guard)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.488322`
- `narrow_passage` / `CX27-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.443666`
- `narrow_passage` / `CX27-A (No-Maze-Guard)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.447187`
- `parasol_misc` / `CX27-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.441617`
- `parasol_misc` / `CX27-A (No-Maze-Guard)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.442665`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`