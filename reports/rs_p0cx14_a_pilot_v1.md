# CX14-A Pilot V1

- protocol: accepted `RS + CX3-D` field locked; CX14 layer trained/selected only on dev data
- chosen params: `{'repeat_penalty': 0.12, 'novelty_bonus': 0.06, 'trap_weight': 0.08, 'corridor_weight': 0.05}`
- output root: `outputs/rs_p0cx14_a_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`0.000`
- exp_delta=`6.571`
- mean_time_overhead_ratio=`1.606644`

## Calib Family Breakdown
- `flange`: success_delta_pp=`0.000`, exp_delta=`4.000`, mean_time_overhead_ratio=`1.707984`
- `maze`: success_delta_pp=`0.000`, exp_delta=`13.333`, mean_time_overhead_ratio=`1.595673`
- `narrow_passage`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`1.516187`
- `parasol_misc`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.719134`

## Public Parasol vs `CX3-D`
- `exp3` / `CX14-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.167`, mean_time_overhead_ratio=`1.707381`
- `exp3` / `CX14-A (No-Novelty)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.703132`
- `exp3` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`0.044303`
- `exp4` / `CX14-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.389`, mean_time_overhead_ratio=`1.709200`
- `exp4` / `CX14-A (No-Novelty)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.704526`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.020539`

## `exp4` Family Breakdown
- `alpha_puzzle` / `CX14-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.579613`
- `alpha_puzzle` / `CX14-A (No-Novelty)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.547902`
- `bug_trap` / `CX14-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.475833`
- `bug_trap` / `CX14-A (No-Novelty)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.456556`
- `flange` / `CX14-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.600`, mean_time_overhead_ratio=`1.709303`
- `flange` / `CX14-A (No-Novelty)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.703984`
- `maze` / `CX14-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.696850`
- `maze` / `CX14-A (No-Novelty)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.686507`
- `narrow_passage` / `CX14-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.500`, mean_time_overhead_ratio=`1.705460`
- `narrow_passage` / `CX14-A (No-Novelty)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.703176`
- `parasol_misc` / `CX14-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.333`, mean_time_overhead_ratio=`1.744394`
- `parasol_misc` / `CX14-A (No-Novelty)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.729942`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`

## Final Readout
- result: public parasol gate is not cleared under the locked dev selection.