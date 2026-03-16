# CX15-D Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow` evaluation; hard-test is consumed only if the public gate clears
- chosen params: `{'depression_margin': 0.14, 'stall_threshold': 0.015, 'accept_ratio_threshold': 0.22, 'repeat_trigger': 2, 'border_radius': 3, 'alignment_bonus': 0.14, 'improvement_bonus': 0.22, 'reverse_bonus': 0.1, 'clearance_w': 0.22, 'corridor_w': 0.24, 'trap_w': 0.32, 'reverse_w': 0.2, 'lateral_w': 0.1, 'forward_w': 0.06, 'heading_w': 0.08, 'stride_cells': 2, 'yaw_stride': 2}`
- output root: `outputs/rs_p0cx15_d_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`0.000`
- exp_delta=`756.286`
- mean_time_overhead_ratio=`0.561131`

## Calib Family Breakdown
- `flange`: exp_delta=`-8.000`, mean_time_overhead_ratio=`0.416199`
- `maze`: exp_delta=`1893.000`, mean_time_overhead_ratio=`0.172534`
- `narrow_passage`: exp_delta=`1.500`, mean_time_overhead_ratio=`0.487360`
- `parasol_misc`: exp_delta=`-380.000`, mean_time_overhead_ratio=`2.019397`

## Public Parasol vs `CX3-D`
- `exp3` / `CX15-D (Full)`: success_delta_pp=`0.000`, exp_delta=`-22.778`, mean_time_overhead_ratio=`0.673936`
- `exp3` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`0.042909`
- `exp4` / `CX15-D (Full)`: success_delta_pp=`0.000`, exp_delta=`-23.222`, mean_time_overhead_ratio=`0.669320`
- `exp4` / `CX15-D (No-Border-Repair)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.211582`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.028351`

## Public `exp4` Family Breakdown
- `alpha_puzzle` / `CX15-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.974281`
- `alpha_puzzle` / `CX15-D (No-Border-Repair)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.274963`
- `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.050884`
- `bug_trap` / `CX15-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`2.586764`
- `bug_trap` / `CX15-D (No-Border-Repair)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.231622`
- `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.219008`
- `flange` / `CX15-D (Full)`: success_delta_pp=`0.000`, exp_delta=`-3.400`, mean_time_overhead_ratio=`0.609689`
- `flange` / `CX15-D (No-Border-Repair)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.211030`
- `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.002614`
- `maze` / `CX15-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.641886`
- `maze` / `CX15-D (No-Border-Repair)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.231945`
- `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.030750`
- `narrow_passage` / `CX15-D (Full)`: success_delta_pp=`0.000`, exp_delta=`-1.750`, mean_time_overhead_ratio=`0.759477`
- `narrow_passage` / `CX15-D (No-Border-Repair)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.205844`
- `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.006491`
- `parasol_misc` / `CX15-D (Full)`: success_delta_pp=`0.000`, exp_delta=`-65.667`, mean_time_overhead_ratio=`0.943942`
- `parasol_misc` / `CX15-D (No-Border-Repair)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.274760`
- `parasol_misc` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-451.500`, mean_time_overhead_ratio=`0.950310`

## Hard Benchmark vs `CX3-D`
- skipped: public gate did not clear, so hard-test evidence was not consumed.

## Hard Family Breakdown
- skipped: no hard-family rows because hard escalation was not triggered.

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`

## Final Readout
- result: public gate not cleared under the locked protocol.