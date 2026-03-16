# CX12-A Pilot V1

- protocol: base sketch locked from `outputs/rs_p0cx10_d_pilot_v1/chosen.json`; CX12 layer trained/selected only on dev data
- chosen params: `{'positive_gain': 150.0, 'negative_loss': 100.0, 'max_depth': 3, 'prob_threshold': 0.35, 'goal_ray_min': 1.0, 'trap_score_max': 3.5}`
- output root: `outputs/rs_p0cx12_a_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`0.000`
- exp_delta=`0.000`
- mean_time_overhead_ratio=`-0.021065`

## Calib Family Breakdown
- `flange`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.039940`
- `maze`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.024934`
- `narrow_passage`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.015488`
- `parasol_misc`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.001737`

## Public Parasol vs `CX3-D`
- `exp3` / `CX10-D (Full)`: success_delta_pp=`-5.556`, exp_delta=`-122.000`, mean_time_overhead_ratio=`-0.011028`
- `exp3` / `CX12-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.302978`
- `exp3` / `CX12-A (No-Hard-Filter)`: success_delta_pp=`-5.556`, exp_delta=`-122.000`, mean_time_overhead_ratio=`-0.008177`
- `exp3` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`-0.266459`
- `exp4` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`-123.111`, mean_time_overhead_ratio=`0.386410`
- `exp4` / `CX12-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.008594`
- `exp4` / `CX12-A (No-Hard-Filter)`: success_delta_pp=`0.000`, exp_delta=`-123.111`, mean_time_overhead_ratio=`0.381355`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.025993`

## `exp4` Family Breakdown
- `alpha_puzzle` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.452018`
- `alpha_puzzle` / `CX12-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.131291`
- `alpha_puzzle` / `CX12-A (No-Hard-Filter)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.464651`
- `bug_trap` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.670019`
- `bug_trap` / `CX12-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.393417`
- `bug_trap` / `CX12-A (No-Hard-Filter)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.635274`
- `flange` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`-522.800`, mean_time_overhead_ratio=`0.419796`
- `flange` / `CX12-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.008763`
- `flange` / `CX12-A (No-Hard-Filter)`: success_delta_pp=`0.000`, exp_delta=`-522.800`, mean_time_overhead_ratio=`0.407619`
- `maze` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.352910`
- `maze` / `CX12-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.008464`
- `maze` / `CX12-A (No-Hard-Filter)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.361022`
- `narrow_passage` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`98.750`, mean_time_overhead_ratio=`0.323265`
- `narrow_passage` / `CX12-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.013170`
- `narrow_passage` / `CX12-A (No-Hard-Filter)`: success_delta_pp=`0.000`, exp_delta=`98.750`, mean_time_overhead_ratio=`0.332010`
- `parasol_misc` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.500`, mean_time_overhead_ratio=`0.344593`
- `parasol_misc` / `CX12-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.034905`
- `parasol_misc` / `CX12-A (No-Hard-Filter)`: success_delta_pp=`0.000`, exp_delta=`0.500`, mean_time_overhead_ratio=`0.344810`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`

## Final Readout
- result: public parasol gate is not cleared under the locked dev selection.