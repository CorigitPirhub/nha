# CX16-C Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow` evaluation; hard-test is consumed only if the public gate clears
- chosen params: `{'trigger_margin': 0.16, 'progress_threshold': 0.012, 'accept_ratio_threshold': 0.25, 'repeat_trigger': 1, 'global_stall_trigger': 2, 'top_macros': 2, 'macro_bonus': 0.08, 'review_bonus': 0.2, 'family_bonus': 0.08, 'clearance_w': 0.22, 'corridor_w': 0.24, 'trap_w': 0.32, 'reverse_w': 0.22, 'lateral_w': 0.1, 'forward_w': 0.06, 'heading_w': 0.08, 'stride_cells': 2, 'yaw_stride': 2, 'horizon_steps': 4}`
- output root: `outputs/rs_p0cx16_c_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`0.000`
- exp_delta=`-24.571`
- mean_time_overhead_ratio=`1.991715`

## Calib Family Breakdown
- `flange`: exp_delta=`-164.000`, mean_time_overhead_ratio=`2.115492`
- `maze`: exp_delta=`-6.333`, mean_time_overhead_ratio=`1.947641`
- `narrow_passage`: exp_delta=`7.500`, mean_time_overhead_ratio=`1.947692`
- `parasol_misc`: exp_delta=`-4.000`, mean_time_overhead_ratio=`2.088205`

## Public Parasol vs `CX3-D`
- `exp3` / `CX16-C (Full)`: success_delta_pp=`0.000`, exp_delta=`-160.667`, mean_time_overhead_ratio=`2.279198`
- `exp3` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`0.042909`
- `exp4` / `CX16-C (Full)`: success_delta_pp=`0.000`, exp_delta=`-169.778`, mean_time_overhead_ratio=`2.198920`
- `exp4` / `CX16-C (No-Review)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.240982`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.028351`

## Public `exp4` Family Breakdown
- `alpha_puzzle` / `CX16-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.612442`
- `alpha_puzzle` / `CX16-C (No-Review)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.298122`
- `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.050884`
- `bug_trap` / `CX16-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.774120`
- `bug_trap` / `CX16-C (No-Review)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.262374`
- `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.219008`
- `flange` / `CX16-C (Full)`: success_delta_pp=`0.000`, exp_delta=`-586.600`, mean_time_overhead_ratio=`2.249582`
- `flange` / `CX16-C (No-Review)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.240279`
- `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.002614`
- `maze` / `CX16-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.894501`
- `maze` / `CX16-C (No-Review)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.251878`
- `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.030750`
- `narrow_passage` / `CX16-C (Full)`: success_delta_pp=`0.000`, exp_delta=`18.500`, mean_time_overhead_ratio=`2.094171`
- `narrow_passage` / `CX16-C (No-Review)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.236298`
- `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.006491`
- `parasol_misc` / `CX16-C (Full)`: success_delta_pp=`0.000`, exp_delta=`-32.833`, mean_time_overhead_ratio=`2.242075`
- `parasol_misc` / `CX16-C (No-Review)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.297604`
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