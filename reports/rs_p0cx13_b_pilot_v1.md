# CX13-B Pilot V1

- protocol: accepted `RS + CX3-D` field locked; CX13 layer trained/selected only on dev data
- chosen params: `{'trap_thr': 0.58, 'corridor_thr': 0.58, 'min_cells': 8, 'prototype_scale': 1.0, 'default_profile': 'cautious'}`
- output root: `outputs/rs_p0cx13_b_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`0.000`
- exp_delta=`0.000`
- mean_time_overhead_ratio=`0.283617`

## Calib Family Breakdown
- `flange`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.278358`
- `maze`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.278433`
- `narrow_passage`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.277570`
- `parasol_misc`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.316519`

## Public Parasol vs `CX3-D`
- `exp3` / `CX13-B (Always-Balanced)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.344774`
- `exp3` / `CX13-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.343079`
- `exp3` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`-0.266459`
- `exp4` / `CX13-B (Always-Balanced)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.911578`
- `exp4` / `CX13-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.909466`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.025993`

## `exp4` Family Breakdown
- `alpha_puzzle` / `CX13-B (Always-Balanced)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.061631`
- `alpha_puzzle` / `CX13-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.058479`
- `bug_trap` / `CX13-B (Always-Balanced)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.128644`
- `bug_trap` / `CX13-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.142682`
- `flange` / `CX13-B (Always-Balanced)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.906328`
- `flange` / `CX13-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.902224`
- `maze` / `CX13-B (Always-Balanced)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.942057`
- `maze` / `CX13-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.940522`
- `narrow_passage` / `CX13-B (Always-Balanced)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.919599`
- `narrow_passage` / `CX13-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.921384`
- `parasol_misc` / `CX13-B (Always-Balanced)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.933282`
- `parasol_misc` / `CX13-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.932435`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`

## Final Readout
- result: public parasol gate is not cleared under the locked dev selection.