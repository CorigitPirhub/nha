# CX16-D Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow` evaluation; hard-test is consumed only if the public gate clears
- chosen params: `{'trigger_margin': 0.14, 'repeat_trigger': 2, 'horizon_steps': 5, 'min_gain': 0.12, 'macro_bonus': 0.12, 'family_bonus': 0.12, 'reverse_bonus': 0.1, 'clearance_w': 0.2, 'corridor_w': 0.26, 'trap_w': 0.34, 'reverse_w': 0.22, 'lateral_w': 0.1, 'forward_w': 0.04, 'heading_w': 0.08, 'stride_cells': 2, 'yaw_stride': 2}`
- output root: `outputs/rs_p0cx16_d_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`0.000`
- exp_delta=`660.571`
- mean_time_overhead_ratio=`0.618078`

## Calib Family Breakdown
- `flange`: exp_delta=`28.000`, mean_time_overhead_ratio=`0.285179`
- `maze`: exp_delta=`1798.333`, mean_time_overhead_ratio=`0.161388`
- `narrow_passage`: exp_delta=`-24.500`, mean_time_overhead_ratio=`0.424289`
- `parasol_misc`: exp_delta=`-750.000`, mean_time_overhead_ratio=`2.708623`

## Public Parasol vs `CX3-D`
- `exp3` / `CX16-D (Full)`: success_delta_pp=`0.000`, exp_delta=`-37.222`, mean_time_overhead_ratio=`0.585138`
- `exp3` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`0.042909`
- `exp4` / `CX16-D (Full)`: success_delta_pp=`0.000`, exp_delta=`-35.667`, mean_time_overhead_ratio=`0.525381`
- `exp4` / `CX16-D (No-Motif)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.234500`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.028351`

## Public `exp4` Family Breakdown
- `alpha_puzzle` / `CX16-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.294200`
- `alpha_puzzle` / `CX16-D (No-Motif)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.291022`
- `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.050884`
- `bug_trap` / `CX16-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.266286`
- `bug_trap` / `CX16-D (No-Motif)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.262559`
- `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.219008`
- `flange` / `CX16-D (Full)`: success_delta_pp=`0.000`, exp_delta=`4.600`, mean_time_overhead_ratio=`0.444592`
- `flange` / `CX16-D (No-Motif)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.231548`
- `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.002614`
- `maze` / `CX16-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.251637`
- `maze` / `CX16-D (No-Motif)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.246735`
- `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.030750`
- `narrow_passage` / `CX16-D (Full)`: success_delta_pp=`0.000`, exp_delta=`21.250`, mean_time_overhead_ratio=`0.632740`
- `narrow_passage` / `CX16-D (No-Motif)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.237733`
- `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.006491`
- `parasol_misc` / `CX16-D (Full)`: success_delta_pp=`0.000`, exp_delta=`-125.000`, mean_time_overhead_ratio=`1.066655`
- `parasol_misc` / `CX16-D (No-Motif)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.259214`
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