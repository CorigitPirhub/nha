# CX11-B Pilot V1

- protocol: base sketch params locked from `outputs/rs_p0cx10_d_pilot_v1/chosen.json`; new CX11 layer trained only on dev data
- chosen params: `{'positive_gain': 50.0, 'max_depth': 2, 'prob_threshold': 0.45, 'min_gates': 1, 'max_overhead': 0.3}`
- output root: `outputs/rs_p0cx11_b_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`0.000`
- exp_delta=`0.000`
- mean_time_overhead_ratio=`0.014645`

## Calib Family Breakdown
- `flange`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.014851`
- `maze`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.009824`
- `narrow_passage`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.013981`
- `parasol_misc`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.030229`

## Public Parasol vs `CX3-D`
- `exp3` / `CX10-D (Full)`: success_delta_pp=`-5.556`, exp_delta=`-122.000`, mean_time_overhead_ratio=`-0.011028`
- `exp3` / `CX11-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.283764`
- `exp3` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`-0.266459`
- `exp4` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`-123.111`, mean_time_overhead_ratio=`0.386410`
- `exp4` / `CX11-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.013676`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.025993`

## `exp4` Family Breakdown
- `alpha_puzzle` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.452018`
- `alpha_puzzle` / `CX11-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.242093`
- `bug_trap` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.670019`
- `bug_trap` / `CX11-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.638523`
- `flange` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`-522.800`, mean_time_overhead_ratio=`0.419796`
- `flange` / `CX11-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.002243`
- `maze` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.352910`
- `maze` / `CX11-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.033940`
- `narrow_passage` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`98.750`, mean_time_overhead_ratio=`0.323265`
- `narrow_passage` / `CX11-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.035006`
- `parasol_misc` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.500`, mean_time_overhead_ratio=`0.344593`
- `parasol_misc` / `CX11-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.027328`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`

## Final Readout
- result: public parasol gate is not cleared under the locked dev selection.