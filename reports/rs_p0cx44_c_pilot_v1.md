# CX44-C Pilot V1

- protocol: unified public rerun against frozen `CX34-A` and `CX41-B`; family-conditional + redundancy-threshold witness transfer; dev-only selection on `calib_hard_v1`; public gate failed so this branch was not advanced to hard eval
- chosen params: `{'review_cell_stride': 3, 'review_yaw_bins': 12, 'margin_thr': 0.03, 'anchor_eps': 0.02, 'enable_parasol_misc': True, 'enable_deadend_labyrinth': True, 'enable_narrow_passage': True, 'min_redundancy': 3}`
- output root: `outputs/rs_p0cx44_c_pilot_v1`

## Public vs `CX34-A (Full)`
- `CX44-C (Full)`: success_delta_pp=`0.000`, exp_delta=`-10.000`, mean_time_overhead_ratio=`0.016996`
- `CX44-C (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`-10.000`, mean_time_overhead_ratio=`0.015654`
- `CX44-C (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`-10.000`, mean_time_overhead_ratio=`0.017629`

## Public Family Breakdown vs `CX34-A (Full)`
- `alpha_puzzle`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.006614`
- `bug_trap`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.006032`
- `flange`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.013612`
- `maze`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.012359`
- `narrow_passage`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.021488`
- `parasol_misc`: exp_delta=`-30.000`, mean_time_overhead_ratio=`0.030740`

## Diagnosis
- This branch produced effectively zero usable witness transfer on public; `witness_hits = 0` across all public cases.
- The redundancy threshold turned the compatibility layer into a pure rejector, so all target-family nodes fell back to `CX34-A` full review while still paying extra bookkeeping cost.
- Because the public gate regressed on `parasol_misc`, the branch was stopped before hard validation.
