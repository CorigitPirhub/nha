# CX16-A Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow` evaluation; hard-test is consumed only if the public gate clears
- chosen params: `{'macro_gate': 0.18, 'reverse_need_thr': 0.08, 'top_macros': 2, 'macro_bonus': 0.06, 'improve_gain': 0.18, 'clearance_w': 0.22, 'corridor_w': 0.24, 'trap_w': 0.3, 'reverse_w': 0.2, 'lateral_w': 0.1, 'forward_w': 0.06, 'heading_w': 0.08, 'stride_cells': 2, 'yaw_stride': 2, 'horizon_steps': 4}`
- output root: `outputs/rs_p0cx16_a_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`0.000`
- exp_delta=`1.429`
- mean_time_overhead_ratio=`0.202296`

## Calib Family Breakdown
- `flange`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.180221`
- `maze`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.172692`
- `narrow_passage`: exp_delta=`5.000`, mean_time_overhead_ratio=`0.243977`
- `parasol_misc`: exp_delta=`0.000`, mean_time_overhead_ratio=`0.229819`

## Public Parasol vs `CX3-D`
- `exp3` / `CX16-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-10.000`, mean_time_overhead_ratio=`0.281643`
- `exp3` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`0.042909`
- `exp4` / `CX16-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-10.000`, mean_time_overhead_ratio=`0.239169`
- `exp4` / `CX16-A (No-Macro-Library)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.170438`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.028351`

## Public `exp4` Family Breakdown
- `alpha_puzzle` / `CX16-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.227731`
- `alpha_puzzle` / `CX16-A (No-Macro-Library)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.233564`
- `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.050884`
- `bug_trap` / `CX16-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.200641`
- `bug_trap` / `CX16-A (No-Macro-Library)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.206243`
- `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.219008`
- `flange` / `CX16-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-0.200`, mean_time_overhead_ratio=`0.219919`
- `flange` / `CX16-A (No-Macro-Library)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.171194`
- `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.002614`
- `maze` / `CX16-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.180928`
- `maze` / `CX16-A (No-Macro-Library)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.180569`
- `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.030750`
- `narrow_passage` / `CX16-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-44.750`, mean_time_overhead_ratio=`0.281551`
- `narrow_passage` / `CX16-A (No-Macro-Library)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.166345`
- `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.006491`
- `parasol_misc` / `CX16-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.209076`
- `parasol_misc` / `CX16-A (No-Macro-Library)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.193662`
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