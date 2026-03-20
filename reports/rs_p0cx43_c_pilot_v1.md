# CX43-C Pilot V1

- protocol: unified public rerun against frozen `CX34-A` and `CX41-B`; inline structural low-entropy release inside `MSRPolicy`; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit
- research anchors:
  - Adaptive Neural Networks for Efficient Inference: https://proceedings.mlr.press/v70/bolukbasi17a.html
  - SelectiveNet / abstain-to-full-policy framing: https://proceedings.mlr.press/v97/geifman19a.html
  - Learning to Defer: https://proceedings.neurips.cc/paper/2018/hash/09d37c08f7b129e96277388757530c72-Abstract.html
- chosen params: `{'margin_thr': 0.06, 'anchor_weight': 0.75, 'guided_weight': 0.25, 'allowed_bonus': 0.04, 'discouraged_penalty': 0.03, 'forbidden_penalty': 0.08, 'macro_bonus': 0.04, 'must_precede_bonus': 0.05}`
- output root: `outputs/rs_p0cx43_c_pilot_v1`

## Public vs `CX3-D`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.388461`
- `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`4.179262`
- `CX43-C (Full)`: success_delta_pp=`0.000`, exp_delta=`422.944`, mean_time_overhead_ratio=`2.548045`
- `CX43-C (No-Rank-Release)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.539522`
- `CX43-C (Proxy-Only)`: success_delta_pp=`0.000`, exp_delta=`523.222`, mean_time_overhead_ratio=`0.841449`

## Public vs `CX34-A (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.704881`
- `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.528500`
- `CX43-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.222`, mean_time_overhead_ratio=`0.047096`
- `CX43-C (No-Rank-Release)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.044581`
- `CX43-C (Proxy-Only)`: success_delta_pp=`0.000`, exp_delta=`100.500`, mean_time_overhead_ratio=`-0.456553`

## Public vs `CX41-B (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.806922`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.345764`
- `CX43-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.222`, mean_time_overhead_ratio=`-0.314952`
- `CX43-C (No-Rank-Release)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.316597`
- `CX43-C (Proxy-Only)`: success_delta_pp=`0.000`, exp_delta=`100.500`, mean_time_overhead_ratio=`-0.644457`

## Public Family Breakdown vs `CX34-A (Full)`
- `alpha_puzzle` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.750955`
- `alpha_puzzle` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.592071`
- `alpha_puzzle` / `CX43-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.039557`
- `alpha_puzzle` / `CX43-C (No-Rank-Release)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.039661`
- `alpha_puzzle` / `CX43-C (Proxy-Only)`: exp_delta=`3.000`, mean_time_overhead_ratio=`-0.548740`
- `bug_trap` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.749300`
- `bug_trap` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.537224`
- `bug_trap` / `CX43-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.056116`
- `bug_trap` / `CX43-C (No-Rank-Release)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.033171`
- `bug_trap` / `CX43-C (Proxy-Only)`: exp_delta=`3.000`, mean_time_overhead_ratio=`-0.721052`
- `flange` / `CX3-D`: exp_delta=`-1428.400`, mean_time_overhead_ratio=`-0.693308`
- `flange` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.485080`
- `flange` / `CX43-C (Full)`: exp_delta=`1.000`, mean_time_overhead_ratio=`0.045828`
- `flange` / `CX43-C (No-Rank-Release)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.041474`
- `flange` / `CX43-C (Proxy-Only)`: exp_delta=`771.000`, mean_time_overhead_ratio=`-0.488933`
- `maze` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.735034`
- `maze` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.655286`
- `maze` / `CX43-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.045530`
- `maze` / `CX43-C (No-Rank-Release)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.051851`
- `maze` / `CX43-C (Proxy-Only)`: exp_delta=`-9.000`, mean_time_overhead_ratio=`-0.399835`
- `narrow_passage` / `CX3-D`: exp_delta=`-98.250`, mean_time_overhead_ratio=`-0.718874`
- `narrow_passage` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.523838`
- `narrow_passage` / `CX43-C (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.049756`
- `narrow_passage` / `CX43-C (No-Rank-Release)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.049915`
- `narrow_passage` / `CX43-C (Proxy-Only)`: exp_delta=`-93.500`, mean_time_overhead_ratio=`-0.440518`
- `parasol_misc` / `CX3-D`: exp_delta=`-12.333`, mean_time_overhead_ratio=`-0.761156`
- `parasol_misc` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.155278`
- `parasol_misc` / `CX43-C (Full)`: exp_delta=`-0.167`, mean_time_overhead_ratio=`0.044432`
- `parasol_misc` / `CX43-C (No-Rank-Release)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.047113`
- `parasol_misc` / `CX43-C (Proxy-Only)`: exp_delta=`-278.167`, mean_time_overhead_ratio=`-0.109136`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`