# CX27-B Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; this round stayed public-first and did not consume hard-test evidence
- chosen params: `{'misc_revisit_thr': 2, 'churn_thr': 0.55, 'loop_thr': 0.15, 'failure_thr': 1, 'progress_eps': 0.02, 'commit_fail_margin': 0.05, 'failure_ttl': 40, 'history_window': 16, 'cell_stride': 2, 'yaw_bins': 24}`
- output root: `outputs/rs_p0cx27_b_pilot_v1`

## Public vs `CX3-D`
- `CX27-B (Full)`: success_delta_pp=`0.000`, exp_delta=`392.889`, mean_time_overhead_ratio=`2.550276`
- `CX27-B (No-Misc-Dampener)`: success_delta_pp=`0.000`, exp_delta=`392.889`, mean_time_overhead_ratio=`2.551211`

## Public Family Breakdown vs `CX3-D`
- `alpha_puzzle` / `CX27-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.971004`
- `alpha_puzzle` / `CX27-B (No-Misc-Dampener)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.972852`
- `bug_trap` / `CX27-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.847668`
- `bug_trap` / `CX27-B (No-Misc-Dampener)`: exp_delta=`0.000`, mean_time_overhead_ratio=`2.819722`
- `flange` / `CX27-B (Full)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.390607`
- `flange` / `CX27-B (No-Misc-Dampener)`: exp_delta=`1428.400`, mean_time_overhead_ratio=`2.391002`
- `maze` / `CX27-B (Full)`: exp_delta=`-113.000`, mean_time_overhead_ratio=`6.121172`
- `maze` / `CX27-B (No-Misc-Dampener)`: exp_delta=`-113.000`, mean_time_overhead_ratio=`6.056250`
- `narrow_passage` / `CX27-B (Full)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.744759`
- `narrow_passage` / `CX27-B (No-Misc-Dampener)`: exp_delta=`98.250`, mean_time_overhead_ratio=`2.744369`
- `parasol_misc` / `CX27-B (Full)`: exp_delta=`-58.333`, mean_time_overhead_ratio=`3.571134`
- `parasol_misc` / `CX27-B (No-Misc-Dampener)`: exp_delta=`-58.333`, mean_time_overhead_ratio=`3.598254`

## Public vs `CX23-C (Full)`
- `CX27-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.504583`
- `CX27-B (No-Misc-Dampener)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.504980`

## Public Family Breakdown vs `CX23-C (Full)`
- `alpha_puzzle` / `CX27-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.490249`
- `alpha_puzzle` / `CX27-B (No-Misc-Dampener)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.490943`
- `bug_trap` / `CX27-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.510544`
- `bug_trap` / `CX27-B (No-Misc-Dampener)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.499573`
- `flange` / `CX27-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.506032`
- `flange` / `CX27-B (No-Misc-Dampener)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.506207`
- `maze` / `CX27-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.505618`
- `maze` / `CX27-B (No-Misc-Dampener)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.491891`
- `narrow_passage` / `CX27-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.504597`
- `narrow_passage` / `CX27-B (No-Misc-Dampener)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.504441`
- `parasol_misc` / `CX27-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.484305`
- `parasol_misc` / `CX27-B (No-Misc-Dampener)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.493111`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`