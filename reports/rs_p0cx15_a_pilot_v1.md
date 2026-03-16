# CX15-A Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow` evaluation; hard-test is consumed only if the public gate clears
- chosen params: `{'margin_gate': 0.18, 'hopeless_margin': 0.03, 'reverse_need_thr': 0.08, 'repeat_trigger': 1, 'improve_gain': 0.28, 'reverse_bonus': 0.12, 'trap_penalty': 0.1, 'hopeless_penalty': 0.1, 'clearance_w': 0.22, 'corridor_w': 0.24, 'trap_w': 0.3, 'reverse_w': 0.18, 'lateral_w': 0.1, 'forward_w': 0.08, 'heading_w': 0.08, 'stride_cells': 2, 'yaw_stride': 2}`
- output root: `outputs/rs_p0cx15_a_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`0.000`
- exp_delta=`-226.143`
- mean_time_overhead_ratio=`1.279175`

## Calib Family Breakdown
- `flange`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.319658`
- `maze`: exp_delta=`-541.667`, mean_time_overhead_ratio=`1.330349`
- `narrow_passage`: exp_delta=`21.000`, mean_time_overhead_ratio=`1.201055`
- `parasol_misc`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.241406`

## Public Parasol vs `CX3-D`
- `exp3` / `CX15-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-0.944`, mean_time_overhead_ratio=`1.290130`
- `exp3` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`0.042909`
- `exp4` / `CX15-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-0.944`, mean_time_overhead_ratio=`1.295769`
- `exp4` / `CX15-A (No-Recoverability)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.166530`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.028351`

## Public `exp4` Family Breakdown
- `alpha_puzzle` / `CX15-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.985818`
- `alpha_puzzle` / `CX15-A (No-Recoverability)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.220827`
- `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.050884`
- `bug_trap` / `CX15-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.806449`
- `bug_trap` / `CX15-A (No-Recoverability)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.200541`
- `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.219008`
- `flange` / `CX15-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.292106`
- `flange` / `CX15-A (No-Recoverability)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.165643`
- `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.002614`
- `maze` / `CX15-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.184069`
- `maze` / `CX15-A (No-Recoverability)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.177787`
- `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.030750`
- `narrow_passage` / `CX15-A (Full)`: success_delta_pp=`0.000`, exp_delta=`3.750`, mean_time_overhead_ratio=`1.304914`
- `narrow_passage` / `CX15-A (No-Recoverability)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.165263`
- `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.006491`
- `parasol_misc` / `CX15-A (Full)`: success_delta_pp=`0.000`, exp_delta=`-5.333`, mean_time_overhead_ratio=`1.287782`
- `parasol_misc` / `CX15-A (No-Recoverability)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.194418`
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