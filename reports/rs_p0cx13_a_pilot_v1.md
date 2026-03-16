# CX13-A Pilot V1

- protocol: accepted `RS + CX3-D` field locked; CX13 layer trained/selected only on dev data
- chosen params: `{'trap_thr': 0.6, 'corridor_thr': 0.58, 'min_cells': 8, 'trap_budget_base': 5, 'trap_budget_scale': 0.9, 'trap_penalty': 0.2, 'reverse_penalty': 0.1, 'corridor_bonus': 0.04}`
- output root: `outputs/rs_p0cx13_a_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`0.000`
- exp_delta=`0.000`
- mean_time_overhead_ratio=`0.291722`

## Calib Family Breakdown
- `flange`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.283668`
- `maze`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.288402`
- `narrow_passage`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.284987`
- `parasol_misc`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.323203`

## Public Parasol vs `CX3-D`
- `exp3` / `CX13-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.348986`
- `exp3` / `CX13-A (No-Budget)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.093810`
- `exp3` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`-0.266459`
- `exp4` / `CX13-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.915084`
- `exp4` / `CX13-A (No-Budget)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.559486`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.025993`

## `exp4` Family Breakdown
- `alpha_puzzle` / `CX13-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.027231`
- `alpha_puzzle` / `CX13-A (No-Budget)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.687600`
- `bug_trap` / `CX13-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.045788`
- `bug_trap` / `CX13-A (No-Budget)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.726053`
- `flange` / `CX13-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.907847`
- `flange` / `CX13-A (No-Budget)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.553734`
- `maze` / `CX13-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.938333`
- `maze` / `CX13-A (No-Budget)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.575764`
- `narrow_passage` / `CX13-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.926816`
- `narrow_passage` / `CX13-A (No-Budget)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.569575`
- `parasol_misc` / `CX13-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.940505`
- `parasol_misc` / `CX13-A (No-Budget)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.572319`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`

## Final Readout
- result: public parasol gate is not cleared under the locked dev selection.