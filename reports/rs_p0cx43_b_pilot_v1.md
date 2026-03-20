# CX43-B Pilot V1

- protocol: unified public rerun against frozen `CX34-A` and `CX41-B`; structural low-entropy release only; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit
- research anchors:
  - Adaptive Neural Networks for Efficient Inference: https://proceedings.mlr.press/v70/bolukbasi17a.html
  - SelectiveNet / abstain-to-full-policy framing: https://proceedings.mlr.press/v97/geifman19a.html
  - Learning to Defer: https://proceedings.neurips.cc/paper/2018/hash/09d37c08f7b129e96277388757530c72-Abstract.html
- chosen params: `{'margin_thr': 0.05, 'anchor_weight': 0.75, 'guided_weight': 0.25, 'allowed_bonus': 0.04, 'discouraged_penalty': 0.03, 'forbidden_penalty': 0.08, 'macro_bonus': 0.04, 'must_precede_bonus': 0.05}`
- output root: `outputs/rs_p0cx43_b_pilot_v1`

## Public vs `CX3-D`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.352828`
- `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`4.180897`
- `CX43-B (Full)`: success_delta_pp=`0.000`, exp_delta=`422.833`, mean_time_overhead_ratio=`2.510768`
- `CX43-B (No-Rank-Release)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`3.439818`
- `CX43-B (Proxy-Only)`: success_delta_pp=`0.000`, exp_delta=`523.222`, mean_time_overhead_ratio=`1.640167`

## Public vs `CX34-A (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.701744`
- `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.545232`
- `CX43-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.111`, mean_time_overhead_ratio=`0.047107`
- `CX43-B (No-Rank-Release)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.324201`
- `CX43-B (Proxy-Only)`: success_delta_pp=`0.000`, exp_delta=`100.500`, mean_time_overhead_ratio=`-0.212555`

## Public vs `CX41-B (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.806983`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.352848`
- `CX43-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.111`, mean_time_overhead_ratio=`-0.322363`
- `CX43-B (No-Rank-Release)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.143041`
- `CX43-B (Proxy-Only)`: success_delta_pp=`0.000`, exp_delta=`100.500`, mean_time_overhead_ratio=`-0.490404`

## Public Family Breakdown vs `CX34-A (Full)`
- `alpha_puzzle` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.744130`
- `alpha_puzzle` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.622904`
- `alpha_puzzle` / `CX43-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.058849`
- `alpha_puzzle` / `CX43-B (No-Rank-Release)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.042132`
- `alpha_puzzle` / `CX43-B (Proxy-Only)`: exp_delta=`3.000`, mean_time_overhead_ratio=`-0.290800`
- `bug_trap` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.740846`
- `bug_trap` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.613291`
- `bug_trap` / `CX43-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.128436`
- `bug_trap` / `CX43-B (No-Rank-Release)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.050591`
- `bug_trap` / `CX43-B (Proxy-Only)`: exp_delta=`3.000`, mean_time_overhead_ratio=`-0.576233`
- `flange` / `CX3-D`: exp_delta=`-1428.400`, mean_time_overhead_ratio=`-0.688258`
- `flange` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.503939`
- `flange` / `CX43-B (Full)`: exp_delta=`1.000`, mean_time_overhead_ratio=`0.047453`
- `flange` / `CX43-B (No-Rank-Release)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.497823`
- `flange` / `CX43-B (Proxy-Only)`: exp_delta=`771.000`, mean_time_overhead_ratio=`-0.260807`
- `maze` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.726918`
- `maze` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.698794`
- `maze` / `CX43-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.052978`
- `maze` / `CX43-B (No-Rank-Release)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.043651`
- `maze` / `CX43-B (Proxy-Only)`: exp_delta=`-9.000`, mean_time_overhead_ratio=`-0.135680`
- `narrow_passage` / `CX3-D`: exp_delta=`-98.250`, mean_time_overhead_ratio=`-0.718318`
- `narrow_passage` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.537446`
- `narrow_passage` / `CX43-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.047984`
- `narrow_passage` / `CX43-B (No-Rank-Release)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.045593`
- `narrow_passage` / `CX43-B (Proxy-Only)`: exp_delta=`-93.500`, mean_time_overhead_ratio=`-0.186889`
- `parasol_misc` / `CX3-D`: exp_delta=`-12.333`, mean_time_overhead_ratio=`-0.764127`
- `parasol_misc` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.155144`
- `parasol_misc` / `CX43-B (Full)`: exp_delta=`-0.500`, mean_time_overhead_ratio=`0.034582`
- `parasol_misc` / `CX43-B (No-Rank-Release)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.038336`
- `parasol_misc` / `CX43-B (Proxy-Only)`: exp_delta=`-278.167`, mean_time_overhead_ratio=`0.281909`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`