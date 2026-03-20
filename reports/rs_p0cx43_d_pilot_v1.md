# CX43-D Pilot V1

- protocol: unified public rerun against frozen `CX34-A` and `CX41-B`; pre-gated structural low-entropy release; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit
- research anchors:
  - Adaptive Neural Networks for Efficient Inference: https://proceedings.mlr.press/v70/bolukbasi17a.html
  - SelectiveNet / abstain-to-full-policy framing: https://proceedings.mlr.press/v97/geifman19a.html
  - Learning to Defer: https://proceedings.neurips.cc/paper/2018/hash/09d37c08f7b129e96277388757530c72-Abstract.html
- chosen params: `{'margin_thr': 0.07, 'anchor_weight': 0.75, 'guided_weight': 0.25, 'allowed_bonus': 0.04, 'discouraged_penalty': 0.03, 'forbidden_penalty': 0.08, 'macro_bonus': 0.04, 'must_precede_bonus': 0.05}`
- output root: `outputs/rs_p0cx43_d_pilot_v1`

## Public vs `CX3-D`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.379691`
- `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`4.179876`
- `CX43-D (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.389467`
- `CX43-D (No-Rank-Release)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.380233`
- `CX43-D (Proxy-Only)`: success_delta_pp=`0.000`, exp_delta=`523.222`, mean_time_overhead_ratio=`0.846305`

## Public vs `CX34-A (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.704115`
- `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.532648`
- `CX43-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.002893`
- `CX43-D (No-Rank-Release)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.000160`
- `CX43-D (Proxy-Only)`: success_delta_pp=`0.000`, exp_delta=`100.500`, mean_time_overhead_ratio=`-0.453706`

## Public vs `CX41-B (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.806945`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.347534`
- `CX43-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.345647`
- `CX43-D (No-Rank-Release)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.347430`
- `CX43-D (Proxy-Only)`: success_delta_pp=`0.000`, exp_delta=`100.500`, mean_time_overhead_ratio=`-0.643562`

## Public Family Breakdown vs `CX34-A (Full)`
- `alpha_puzzle` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.748876`
- `alpha_puzzle` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.595127`
- `alpha_puzzle` / `CX43-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.001905`
- `alpha_puzzle` / `CX43-D (No-Rank-Release)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.003403`
- `alpha_puzzle` / `CX43-D (Proxy-Only)`: exp_delta=`3.000`, mean_time_overhead_ratio=`-0.545838`
- `bug_trap` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.753696`
- `bug_trap` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.548063`
- `bug_trap` / `CX43-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.001547`
- `bug_trap` / `CX43-D (No-Rank-Release)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.004465`
- `bug_trap` / `CX43-D (Proxy-Only)`: exp_delta=`3.000`, mean_time_overhead_ratio=`-0.723357`
- `flange` / `CX3-D`: exp_delta=`-1428.400`, mean_time_overhead_ratio=`-0.690529`
- `flange` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.492930`
- `flange` / `CX43-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.003288`
- `flange` / `CX43-D (No-Rank-Release)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.001643`
- `flange` / `CX43-D (Proxy-Only)`: exp_delta=`771.000`, mean_time_overhead_ratio=`-0.486317`
- `maze` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.732960`
- `maze` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.653138`
- `maze` / `CX43-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.001356`
- `maze` / `CX43-D (No-Rank-Release)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.001642`
- `maze` / `CX43-D (Proxy-Only)`: exp_delta=`-9.000`, mean_time_overhead_ratio=`-0.401987`
- `narrow_passage` / `CX3-D`: exp_delta=`-98.250`, mean_time_overhead_ratio=`-0.722627`
- `narrow_passage` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.521692`
- `narrow_passage` / `CX43-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.002371`
- `narrow_passage` / `CX43-D (No-Rank-Release)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.002073`
- `narrow_passage` / `CX43-D (Proxy-Only)`: exp_delta=`-93.500`, mean_time_overhead_ratio=`-0.438920`
- `parasol_misc` / `CX3-D`: exp_delta=`-12.333`, mean_time_overhead_ratio=`-0.752506`
- `parasol_misc` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.151039`
- `parasol_misc` / `CX43-D (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.001374`
- `parasol_misc` / `CX43-D (No-Rank-Release)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.003465`
- `parasol_misc` / `CX43-D (Proxy-Only)`: exp_delta=`-278.167`, mean_time_overhead_ratio=`-0.095877`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`