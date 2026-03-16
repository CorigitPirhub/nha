# CX15-C Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow` evaluation; hard-test is consumed only if the public gate clears
- chosen params: `{'trap_threshold': 0.44, 'min_escape_gain': 0.14, 'horizon_steps': 4, 'trigger_margin': 0.14, 'repeat_trigger': 2, 'family_bonus': 0.14, 'reverse_bonus': 0.1, 'clearance_w': 0.22, 'corridor_w': 0.24, 'trap_w': 0.32, 'reverse_w': 0.2, 'lateral_w': 0.1, 'forward_w': 0.06, 'heading_w': 0.08, 'stride_cells': 2, 'yaw_stride': 2}`
- output root: `outputs/rs_p0cx15_c_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`0.000`
- exp_delta=`-2.286`
- mean_time_overhead_ratio=`0.339907`

## Calib Family Breakdown
- `flange`: exp_delta=`-12.000`, mean_time_overhead_ratio=`0.263457`
- `maze`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.250344`
- `narrow_passage`: exp_delta=`-4.000`, mean_time_overhead_ratio=`0.292437`
- `parasol_misc`: exp_delta=`4.000`, mean_time_overhead_ratio=`0.779985`

## Public Parasol vs `CX3-D`
- `exp3` / `CX15-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.389`, mean_time_overhead_ratio=`0.402889`
- `exp3` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`0.042909`
- `exp4` / `CX15-C (Full)`: success_delta_pp=`0.000`, exp_delta=`-0.278`, mean_time_overhead_ratio=`0.389232`
- `exp4` / `CX15-C (No-Memory)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.245052`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.028351`

## Public `exp4` Family Breakdown
- `alpha_puzzle` / `CX15-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.301814`
- `alpha_puzzle` / `CX15-C (No-Memory)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.306065`
- `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.050884`
- `bug_trap` / `CX15-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.271042`
- `bug_trap` / `CX15-C (No-Memory)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.283800`
- `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.219008`
- `flange` / `CX15-C (Full)`: success_delta_pp=`0.000`, exp_delta=`-2.400`, mean_time_overhead_ratio=`0.336275`
- `flange` / `CX15-C (No-Memory)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.243806`
- `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.002614`
- `maze` / `CX15-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.263808`
- `maze` / `CX15-C (No-Memory)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.261887`
- `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.030750`
- `narrow_passage` / `CX15-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.750`, mean_time_overhead_ratio=`0.490356`
- `narrow_passage` / `CX15-C (No-Memory)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.244582`
- `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.006491`
- `parasol_misc` / `CX15-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.667`, mean_time_overhead_ratio=`0.450859`
- `parasol_misc` / `CX15-C (No-Memory)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.271889`
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