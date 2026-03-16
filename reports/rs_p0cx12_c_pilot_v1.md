# CX12-C Pilot V1

- protocol: base sketch locked from `outputs/rs_p0cx10_d_pilot_v1/chosen.json`; CX12 layer trained/selected only on dev data
- chosen params: `{'positive_gain': 50.0, 'negative_loss': 50.0, 'max_depth': 2, 'prob_threshold': 0.45, 'min_depth': 3, 'stall_progress_max': 0.12, 'near_gate_radius_m': 3.0}`
- output root: `outputs/rs_p0cx12_c_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`0.000`
- exp_delta=`0.000`
- mean_time_overhead_ratio=`-0.015912`

## Calib Family Breakdown
- `flange`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.024705`
- `maze`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.021843`
- `narrow_passage`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.015132`
- `parasol_misc`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.009112`

## Public Parasol vs `CX3-D`
- `exp3` / `CX10-D (Full)`: success_delta_pp=`-5.556`, exp_delta=`-122.000`, mean_time_overhead_ratio=`-0.011028`
- `exp3` / `CX12-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.297319`
- `exp3` / `CX12-C (No-State-Gate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.299258`
- `exp3` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`-0.266459`
- `exp4` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`-123.111`, mean_time_overhead_ratio=`0.386410`
- `exp4` / `CX12-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.000538`
- `exp4` / `CX12-C (No-State-Gate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.000744`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.025993`

## `exp4` Family Breakdown
- `alpha_puzzle` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.452018`
- `alpha_puzzle` / `CX12-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.177832`
- `alpha_puzzle` / `CX12-C (No-State-Gate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.212686`
- `bug_trap` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.670019`
- `bug_trap` / `CX12-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.485913`
- `bug_trap` / `CX12-C (No-State-Gate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.497352`
- `flange` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`-522.800`, mean_time_overhead_ratio=`0.419796`
- `flange` / `CX12-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.001300`
- `flange` / `CX12-C (No-State-Gate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.000348`
- `maze` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.352910`
- `maze` / `CX12-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.015466`
- `maze` / `CX12-C (No-State-Gate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.023370`
- `narrow_passage` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`98.750`, mean_time_overhead_ratio=`0.323265`
- `narrow_passage` / `CX12-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.002942`
- `narrow_passage` / `CX12-C (No-State-Gate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.001208`
- `parasol_misc` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.500`, mean_time_overhead_ratio=`0.344593`
- `parasol_misc` / `CX12-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.010119`
- `parasol_misc` / `CX12-C (No-State-Gate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.013695`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`

## Final Readout
- result: public parasol gate is not cleared under the locked dev selection.