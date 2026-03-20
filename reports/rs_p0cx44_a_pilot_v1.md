# CX44-A Pilot V1

- protocol: unified public rerun against frozen `CX34-A` and `CX41-B`; representative macro review contract; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit
- research anchors:
  - Experience Graphs / reusable planning structure: https://www.ri.cmu.edu/publications/experience-graphs-leveraging-multiple-planning-graphs-in-motion-planning/
  - LazySP / lazy expensive operator evaluation: https://arxiv.org/abs/1707.04015
  - SelectiveNet: https://proceedings.mlr.press/v97/geifman19a.html
- chosen params: `{'review_cell_stride': 3, 'review_yaw_bins': 12, 'margin_thr': 0.04, 'anchor_eps': 0.02}`
- output root: `outputs/rs_p0cx44_a_pilot_v1`

## Public vs `CX3-D`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.399909`
- `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`4.206057`
- `CX44-A (Full)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.431942`
- `CX44-A (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`422.722`, mean_time_overhead_ratio=`2.427079`
- `CX44-A (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`-71.667`, mean_time_overhead_ratio=`2.572512`

## Public vs `CX34-A (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.705874`
- `CX41-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.531234`
- `CX44-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.009422`
- `CX44-A (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.007991`
- `CX44-A (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`-494.389`, mean_time_overhead_ratio=`0.050767`

## Public vs `CX41-B (Full)`
- `CX3-D`: success_delta_pp=`0.000`, exp_delta=`-422.722`, mean_time_overhead_ratio=`-0.807916`
- `CX34-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.346932`
- `CX44-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.340779`
- `CX44-A (No-Witness-Transfer)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.341713`
- `CX44-A (Proxy-Only-Negative)`: success_delta_pp=`0.000`, exp_delta=`-494.389`, mean_time_overhead_ratio=`-0.313778`

## Public Family Breakdown vs `CX34-A (Full)`
- `alpha_puzzle` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.761864`
- `alpha_puzzle` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.558106`
- `alpha_puzzle` / `CX44-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.014481`
- `alpha_puzzle` / `CX44-A (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.020200`
- `alpha_puzzle` / `CX44-A (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.096136`
- `bug_trap` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.769999`
- `bug_trap` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.484112`
- `bug_trap` / `CX44-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.021761`
- `bug_trap` / `CX44-A (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.009496`
- `bug_trap` / `CX44-A (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.088778`
- `flange` / `CX3-D`: exp_delta=`-1428.400`, mean_time_overhead_ratio=`-0.691259`
- `flange` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.490745`
- `flange` / `CX44-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.013534`
- `flange` / `CX44-A (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.007894`
- `flange` / `CX44-A (Proxy-Only-Negative)`: exp_delta=`-1621.000`, mean_time_overhead_ratio=`0.101633`
- `maze` / `CX3-D`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.737330`
- `maze` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.658429`
- `maze` / `CX44-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.013035`
- `maze` / `CX44-A (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.004056`
- `maze` / `CX44-A (Proxy-Only-Negative)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.001551`
- `narrow_passage` / `CX3-D`: exp_delta=`-98.250`, mean_time_overhead_ratio=`-0.724658`
- `narrow_passage` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.522692`
- `narrow_passage` / `CX44-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.005012`
- `narrow_passage` / `CX44-A (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.008237`
- `narrow_passage` / `CX44-A (Proxy-Only-Negative)`: exp_delta=`-168.250`, mean_time_overhead_ratio=`-0.021368`
- `parasol_misc` / `CX3-D`: exp_delta=`-12.333`, mean_time_overhead_ratio=`-0.766802`
- `parasol_misc` / `CX41-B (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.138993`
- `parasol_misc` / `CX44-A (Full)`: exp_delta=`0.000`, mean_time_overhead_ratio=`-0.015371`
- `parasol_misc` / `CX44-A (No-Witness-Transfer)`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.008163`
- `parasol_misc` / `CX44-A (Proxy-Only-Negative)`: exp_delta=`-20.167`, mean_time_overhead_ratio=`-0.110036`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`