# CX14-C Pilot V1

- protocol: accepted `RS + CX3-D` field locked; CX14 layer trained/selected only on dev data
- chosen params: `{'novelty_penalty': 0.08, 'trap_weight': 0.05, 'corridor_bonus': 0.03, 'stagnation_window': 4, 'switch_progress': 0.02}`
- output root: `outputs/rs_p0cx14_c_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`0.000`
- exp_delta=`6.571`
- mean_time_overhead_ratio=`1.749977`

## Calib Family Breakdown
- `flange`: success_delta_pp=`0.000`, exp_delta=`4.000`, mean_time_overhead_ratio=`1.865800`
- `maze`: success_delta_pp=`0.000`, exp_delta=`13.333`, mean_time_overhead_ratio=`1.737317`
- `narrow_passage`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`1.649567`
- `parasol_misc`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.872954`

## Public Parasol vs `CX3-D`
- `exp3` / `CX14-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.167`, mean_time_overhead_ratio=`1.854976`
- `exp3` / `CX14-C (Static-Mix)`: success_delta_pp=`0.000`, exp_delta=`0.167`, mean_time_overhead_ratio=`1.853654`
- `exp3` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`0.039807`
- `exp4` / `CX14-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.389`, mean_time_overhead_ratio=`1.854265`
- `exp4` / `CX14-C (Static-Mix)`: success_delta_pp=`0.000`, exp_delta=`0.389`, mean_time_overhead_ratio=`1.853218`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.015953`

## `exp4` Family Breakdown
- `alpha_puzzle` / `CX14-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.661870`
- `alpha_puzzle` / `CX14-C (Static-Mix)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.673179`
- `bug_trap` / `CX14-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.531606`
- `bug_trap` / `CX14-C (Static-Mix)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.529882`
- `flange` / `CX14-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.600`, mean_time_overhead_ratio=`1.849911`
- `flange` / `CX14-C (Static-Mix)`: success_delta_pp=`0.000`, exp_delta=`0.600`, mean_time_overhead_ratio=`1.850161`
- `maze` / `CX14-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.813278`
- `maze` / `CX14-C (Static-Mix)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.841573`
- `narrow_passage` / `CX14-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.500`, mean_time_overhead_ratio=`1.860587`
- `narrow_passage` / `CX14-C (Static-Mix)`: success_delta_pp=`0.000`, exp_delta=`0.500`, mean_time_overhead_ratio=`1.851883`
- `parasol_misc` / `CX14-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.333`, mean_time_overhead_ratio=`1.881420`
- `parasol_misc` / `CX14-C (Static-Mix)`: success_delta_pp=`0.000`, exp_delta=`0.333`, mean_time_overhead_ratio=`1.926335`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`

## Final Readout
- result: public parasol gate is not cleared under the locked dev selection.