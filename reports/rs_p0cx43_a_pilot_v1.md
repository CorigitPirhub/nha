# CX43-A Pilot V1

- protocol: unified public rerun against frozen `CX34-A` and `CX41-B`; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit
- research anchors:
  - Adaptive Neural Networks for Efficient Inference: https://proceedings.mlr.press/v70/bolukbasi17a.html
  - SelectiveNet / abstain-to-full-policy framing: https://proceedings.mlr.press/v97/geifman19a.html
  - Learning to Defer: https://proceedings.neurips.cc/paper/2018/hash/09d37c08f7b129e96277388757530c72-Abstract.html
  - Experience Graphs / reusable planning structure: https://www.ri.cmu.edu/publications/experience-graphs-leveraging-multiple-planning-graphs-in-motion-planning/
- chosen params: `{'min_hits': 8, 'support_slack': 0.0, 'anchor_weight': 0.75, 'guided_weight': 0.25, 'allowed_bonus': 0.04, 'discouraged_penalty': 0.03, 'forbidden_penalty': 0.08, 'macro_bonus': 0.04, 'must_precede_bonus': 0.05}`
- output root: `outputs/rs_p0cx43_a_pilot_v1`

## Public vs `CX3-D`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.420113`
- `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`4.212689`
- `CX43-A (Full)`: success_delta_pp=`0.000`, exp_delta=`355.778`, mean_time_overhead_ratio=`2.497649`
- `CX43-A (No-Rank-Release)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.548575`
- `CX43-A (Proxy-Only)`: success_delta_pp=`0.000`, exp_delta=`523.222`, mean_time_overhead_ratio=`0.878249`

## Public vs `CX34-A (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.707612`
- `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.524128`
- `CX43-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-66.944`, mean_time_overhead_ratio=`0.022671`
- `CX43-A (No-Rank-Release)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.037561`
- `CX43-A (Proxy-Only)`: success_delta_pp=`0.000`, exp_delta=`100.500`, mean_time_overhead_ratio=`-0.450823`

## Public vs `CX41-B (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.808160`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.343887`
- `CX43-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-66.944`, mean_time_overhead_ratio=`-0.329012`
- `CX43-A (No-Rank-Release)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.319243`
- `CX43-A (Proxy-Only)`: success_delta_pp=`0.000`, exp_delta=`100.500`, mean_time_overhead_ratio=`-0.639678`

## Public Family Breakdown vs `CX34-A (Full)`
- `alpha_puzzle` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.748881`
- `alpha_puzzle` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.713308`
- `alpha_puzzle` / `CX43-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.099616`
- `alpha_puzzle` / `CX43-A (No-Rank-Release)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.041374`
- `alpha_puzzle` / `CX43-A (Proxy-Only)`: exp_delta=`3.000`, mean_time_overhead_ratio=`-0.518900`
- `bug_trap` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.751861`
- `bug_trap` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.688830`
- `bug_trap` / `CX43-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.098850`
- `bug_trap` / `CX43-A (No-Rank-Release)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.055801`
- `bug_trap` / `CX43-A (Proxy-Only)`: exp_delta=`3.000`, mean_time_overhead_ratio=`-0.718553`
- `flange` / `CX3-D`: exp_delta=`-1428.400`, mean_time_overhead_ratio=`-0.694692`
- `flange` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.478929`
- `flange` / `CX43-A (Full)`: exp_delta=`-233.800`, mean_time_overhead_ratio=`0.067088`
- `flange` / `CX43-A (No-Rank-Release)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.033572`
- `flange` / `CX43-A (Proxy-Only)`: exp_delta=`771.000`, mean_time_overhead_ratio=`-0.482837`
- `maze` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.738820`
- `maze` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.660721`
- `maze` / `CX43-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.065144`
- `maze` / `CX43-A (No-Rank-Release)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.051439`
- `maze` / `CX43-A (Proxy-Only)`: exp_delta=`-9.000`, mean_time_overhead_ratio=`-0.404693`
- `narrow_passage` / `CX3-D`: exp_delta=`-98.250`, mean_time_overhead_ratio=`-0.723929`
- `narrow_passage` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.524348`
- `narrow_passage` / `CX43-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.062775`
- `narrow_passage` / `CX43-A (No-Rank-Release)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.045758`
- `narrow_passage` / `CX43-A (Proxy-Only)`: exp_delta=`-93.500`, mean_time_overhead_ratio=`-0.435414`
- `parasol_misc` / `CX3-D`: exp_delta=`-12.333`, mean_time_overhead_ratio=`-0.765106`
- `parasol_misc` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.130704`
- `parasol_misc` / `CX43-A (Full)`: exp_delta=`-6.000`, mean_time_overhead_ratio=`0.050592`
- `parasol_misc` / `CX43-A (No-Rank-Release)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.029999`
- `parasol_misc` / `CX43-A (Proxy-Only)`: exp_delta=`-278.167`, mean_time_overhead_ratio=`-0.106148`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`