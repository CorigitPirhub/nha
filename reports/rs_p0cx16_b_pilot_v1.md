# CX16-B Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow` evaluation; hard-test is consumed only if the public gate clears
- chosen params: `{'oracle_gain_thr': 0.03, 'margin_gate': 0.16, 'hopeless_margin': 0.03, 'repeat_trigger': 1, 'improve_gain': 0.2, 'reverse_bonus': 0.1, 'hopeless_penalty': 0.08, 'table_gain_weight': 0.1, 'clearance_w': 0.22, 'corridor_w': 0.24, 'trap_w': 0.32, 'reverse_w': 0.22, 'lateral_w': 0.1, 'forward_w': 0.06, 'heading_w': 0.08, 'stride_cells': 2, 'yaw_stride': 2, 'horizon_steps': 4}`
- output root: `outputs/rs_p0cx16_b_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`0.000`
- exp_delta=`-226.000`
- mean_time_overhead_ratio=`1.288266`

## Calib Family Breakdown
- `flange`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.303430`
- `maze`: exp_delta=`-541.667`, mean_time_overhead_ratio=`1.326945`
- `narrow_passage`: exp_delta=`21.500`, mean_time_overhead_ratio=`1.210993`
- `parasol_misc`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.311615`

## Public Parasol vs `CX3-D`
- `exp3` / `CX16-B (Full)`: success_delta_pp=`0.000`, exp_delta=`11.556`, mean_time_overhead_ratio=`1.299771`
- `exp3` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`0.042909`
- `exp4` / `CX16-B (Full)`: success_delta_pp=`0.000`, exp_delta=`11.556`, mean_time_overhead_ratio=`1.309856`
- `exp4` / `CX16-B (No-Oracle)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.233832`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.028351`

## Public `exp4` Family Breakdown
- `alpha_puzzle` / `CX16-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.017990`
- `alpha_puzzle` / `CX16-B (No-Oracle)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.284296`
- `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.050884`
- `bug_trap` / `CX16-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.830966`
- `bug_trap` / `CX16-B (No-Oracle)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.263169`
- `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.219008`
- `flange` / `CX16-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.312076`
- `flange` / `CX16-B (No-Oracle)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.232932`
- `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.002614`
- `maze` / `CX16-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.195898`
- `maze` / `CX16-B (No-Oracle)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.250945`
- `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.030750`
- `narrow_passage` / `CX16-B (Full)`: success_delta_pp=`0.000`, exp_delta=`60.000`, mean_time_overhead_ratio=`1.305503`
- `narrow_passage` / `CX16-B (No-Oracle)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.232676`
- `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.006491`
- `parasol_misc` / `CX16-B (Full)`: success_delta_pp=`0.000`, exp_delta=`-5.333`, mean_time_overhead_ratio=`1.317175`
- `parasol_misc` / `CX16-B (No-Oracle)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.260638`
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