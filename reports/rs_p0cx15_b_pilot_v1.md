# CX15-B Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow` evaluation; hard-test is consumed only if the public gate clears
- chosen params: `{'trigger_margin': 0.18, 'stall_threshold': 0.01, 'accept_ratio_threshold': 0.28, 'repeat_trigger': 1, 'global_stall_trigger': 1, 'improve_gain': 0.24, 'family_bonus': 0.08, 'reverse_bonus': 0.08, 'top_families': 2, 'clearance_w': 0.24, 'corridor_w': 0.22, 'trap_w': 0.28, 'reverse_w': 0.18, 'lateral_w': 0.1, 'forward_w': 0.08, 'heading_w': 0.08, 'stride_cells': 2, 'yaw_stride': 2}`
- output root: `outputs/rs_p0cx15_b_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`0.000`
- exp_delta=`174.571`
- mean_time_overhead_ratio=`1.431252`

## Calib Family Breakdown
- `flange`: exp_delta=`190.000`, mean_time_overhead_ratio=`1.342752`
- `maze`: exp_delta=`454.667`, mean_time_overhead_ratio=`1.270368`
- `narrow_passage`: exp_delta=`20.500`, mean_time_overhead_ratio=`1.299120`
- `parasol_misc`: exp_delta=`-373.000`, mean_time_overhead_ratio=`2.266670`

## Public Parasol vs `CX3-D`
- `exp3` / `CX15-B (Full)`: success_delta_pp=`0.000`, exp_delta=`-112.333`, mean_time_overhead_ratio=`1.474832`
- `exp3` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`0.042909`
- `exp4` / `CX15-B (Always-Trigger)`: success_delta_pp=`0.000`, exp_delta=`-101.778`, mean_time_overhead_ratio=`1.409536`
- `exp4` / `CX15-B (Full)`: success_delta_pp=`0.000`, exp_delta=`-101.778`, mean_time_overhead_ratio=`1.412248`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.028351`

## Public `exp4` Family Breakdown
- `alpha_puzzle` / `CX15-B (Always-Trigger)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.419780`
- `alpha_puzzle` / `CX15-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.442787`
- `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.050884`
- `bug_trap` / `CX15-B (Always-Trigger)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.372364`
- `bug_trap` / `CX15-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.383991`
- `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.219008`
- `flange` / `CX15-B (Always-Trigger)`: success_delta_pp=`0.000`, exp_delta=`-242.400`, mean_time_overhead_ratio=`1.403918`
- `flange` / `CX15-B (Full)`: success_delta_pp=`0.000`, exp_delta=`-242.400`, mean_time_overhead_ratio=`1.407471`
- `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.002614`
- `maze` / `CX15-B (Always-Trigger)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.376103`
- `maze` / `CX15-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.377970`
- `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.030750`
- `narrow_passage` / `CX15-B (Always-Trigger)`: success_delta_pp=`0.000`, exp_delta=`-49.250`, mean_time_overhead_ratio=`1.385344`
- `narrow_passage` / `CX15-B (Full)`: success_delta_pp=`0.000`, exp_delta=`-49.250`, mean_time_overhead_ratio=`1.386324`
- `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.006491`
- `parasol_misc` / `CX15-B (Always-Trigger)`: success_delta_pp=`0.000`, exp_delta=`-70.500`, mean_time_overhead_ratio=`1.746326`
- `parasol_misc` / `CX15-B (Full)`: success_delta_pp=`0.000`, exp_delta=`-70.500`, mean_time_overhead_ratio=`1.749252`
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