# CX14-B Pilot V1

- protocol: accepted `RS + CX3-D` field locked; CX14 layer trained/selected only on dev data
- chosen params: `{'base_penalty': 0.08, 'update_gain': 0.14, 'stall_threshold': 0.03, 'trap_weight': 0.06}`
- output root: `outputs/rs_p0cx14_b_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`0.000`
- exp_delta=`7.000`
- mean_time_overhead_ratio=`1.471205`

## Calib Family Breakdown
- `flange`: success_delta_pp=`0.000`, exp_delta=`6.000`, mean_time_overhead_ratio=`1.568946`
- `maze`: success_delta_pp=`0.000`, exp_delta=`13.667`, mean_time_overhead_ratio=`1.458744`
- `narrow_passage`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`1.384481`
- `parasol_misc`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.584292`

## Public Parasol vs `CX3-D`
- `exp3` / `CX14-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.111`, mean_time_overhead_ratio=`1.578762`
- `exp3` / `CX14-B (No-Update)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.502687`
- `exp3` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`0.042909`
- `exp4` / `CX14-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.444`, mean_time_overhead_ratio=`1.582221`
- `exp4` / `CX14-B (No-Update)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.496558`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.028351`

## `exp4` Family Breakdown
- `alpha_puzzle` / `CX14-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.413900`
- `alpha_puzzle` / `CX14-B (No-Update)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.375114`
- `bug_trap` / `CX14-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.328127`
- `bug_trap` / `CX14-B (No-Update)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.266563`
- `flange` / `CX14-B (Full)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`1.586264`
- `flange` / `CX14-B (No-Update)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.482932`
- `maze` / `CX14-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.533740`
- `maze` / `CX14-B (No-Update)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.487788`
- `narrow_passage` / `CX14-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.500`, mean_time_overhead_ratio=`1.573993`
- `narrow_passage` / `CX14-B (No-Update)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.517516`
- `parasol_misc` / `CX14-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.167`, mean_time_overhead_ratio=`1.586825`
- `parasol_misc` / `CX14-B (No-Update)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.559961`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`

## Final Readout
- result: public parasol gate is not cleared under the locked dev selection.