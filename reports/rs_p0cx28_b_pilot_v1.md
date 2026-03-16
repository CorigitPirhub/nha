# CX28-B Pilot V1

- protocol: frozen `CX27-A / Maze Depression Guard` parent; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; no hard-test evidence consumed
- chosen params: `{'maze_revisit_thr': 2, 'maze_stall_steps': 18, 'reverse_required_thr': 0.1, 'trap_thr': 0.54, 'misc_revisit_thr': 1, 'misc_churn_thr': 0.15, 'switch_margin': 0.01, 'abstain_margin': -0.01, 'block_ttl': 40, 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 32, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24}`
- output root: `outputs/rs_p0cx28_b_pilot_v1`

## Public vs `CX3-D`
- `CX28-B (Full)`: success_delta_pp=`0.000`, exp_delta=`397.056`, mean_time_overhead_ratio=`2.601315`
- `CX28-B (No-Class-Precondition)`: success_delta_pp=`0.000`, exp_delta=`399.167`, mean_time_overhead_ratio=`2.551501`

## Public Family Breakdown vs `CX3-D`
- `alpha_puzzle` / `CX28-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.986583`
- `alpha_puzzle` / `CX28-B (No-Class-Precondition)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.961224`
- `bug_trap` / `CX28-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.865733`
- `bug_trap` / `CX28-B (No-Class-Precondition)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.814287`
- `flange` / `CX28-B (Full)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.433373`
- `flange` / `CX28-B (No-Class-Precondition)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.382246`
- `maze` / `CX28-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.924269`
- `maze` / `CX28-B (No-Class-Precondition)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.852768`
- `narrow_passage` / `CX28-B (Full)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.790181`
- `narrow_passage` / `CX28-B (No-Class-Precondition)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.756985`
- `parasol_misc` / `CX28-B (Full)`: exp_delta=`-64.667`, mean_time_overhead_ratio=`3.997947`
- `parasol_misc` / `CX28-B (No-Class-Precondition)`: exp_delta=`-58.333`, mean_time_overhead_ratio=`3.817402`

## Public vs `CX27-A (Full)`
- `CX28-B (Full)`: success_delta_pp=`0.000`, exp_delta=`-2.111`, mean_time_overhead_ratio=`0.059760`
- `CX28-B (No-Class-Precondition)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.045102`

## Public Family Breakdown vs `CX27-A (Full)`
- `alpha_puzzle` / `CX28-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.035532`
- `alpha_puzzle` / `CX28-B (No-Class-Precondition)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.028945`
- `bug_trap` / `CX28-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.037488`
- `bug_trap` / `CX28-B (No-Class-Precondition)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.023681`
- `flange` / `CX28-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.057714`
- `flange` / `CX28-B (No-Class-Precondition)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.041963`
- `maze` / `CX28-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.063355`
- `maze` / `CX28-B (No-Class-Precondition)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.043981`
- `narrow_passage` / `CX28-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.054848`
- `narrow_passage` / `CX28-B (No-Class-Precondition)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.045609`
- `parasol_misc` / `CX28-B (Full)`: exp_delta=`-6.333`, mean_time_overhead_ratio=`0.125748`
- `parasol_misc` / `CX28-B (No-Class-Precondition)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.085081`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
