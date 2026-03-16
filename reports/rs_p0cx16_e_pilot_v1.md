# CX16-E Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow` evaluation; hard-test is consumed only if the public gate clears
- chosen params: `{'macro_gate': 0.16, 'border_radius': 2, 'top_macros': 3, 'macro_bonus': 0.08, 'border_align_bonus': 0.12, 'review_gain': 0.2, 'repeat_trigger': 1, 'clearance_w': 0.22, 'corridor_w': 0.24, 'trap_w': 0.32, 'reverse_w': 0.22, 'lateral_w': 0.1, 'forward_w': 0.06, 'heading_w': 0.08, 'stride_cells': 2, 'yaw_stride': 2, 'horizon_steps': 4}`
- output root: `outputs/rs_p0cx16_e_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`-14.286`
- exp_delta=`1044.714`
- mean_time_overhead_ratio=`2.241024`

## Calib Family Breakdown
- `flange`: exp_delta=`2891.000`, mean_time_overhead_ratio=`1.508911`
- `maze`: exp_delta=`1576.000`, mean_time_overhead_ratio=`1.905648`
- `narrow_passage`: exp_delta=`66.500`, mean_time_overhead_ratio=`2.219923`
- `parasol_misc`: exp_delta=`-439.000`, mean_time_overhead_ratio=`4.021469`

## Public Parasol vs `CX3-D`
- `exp3` / `CX16-E (Full)`: success_delta_pp=`-5.556`, exp_delta=`-208.556`, mean_time_overhead_ratio=`2.721234`
- `exp3` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`0.042909`
- `exp4` / `CX16-E (Full)`: success_delta_pp=`0.000`, exp_delta=`-58.722`, mean_time_overhead_ratio=`2.478006`
- `exp4` / `CX16-E (No-Substrate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.242104`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.028351`

## Public `exp4` Family Breakdown
- `alpha_puzzle` / `CX16-E (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`2.914356`
- `alpha_puzzle` / `CX16-E (No-Substrate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.295573`
- `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.050884`
- `bug_trap` / `CX16-E (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`3.135128`
- `bug_trap` / `CX16-E (No-Substrate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.268728`
- `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.219008`
- `flange` / `CX16-E (Full)`: success_delta_pp=`0.000`, exp_delta=`-46.600`, mean_time_overhead_ratio=`2.440838`
- `flange` / `CX16-E (No-Substrate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.241791`
- `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.002614`
- `maze` / `CX16-E (Full)`: success_delta_pp=`0.000`, exp_delta=`-14.000`, mean_time_overhead_ratio=`2.816398`
- `maze` / `CX16-E (No-Substrate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.252685`
- `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.030750`
- `narrow_passage` / `CX16-E (Full)`: success_delta_pp=`0.000`, exp_delta=`-22.500`, mean_time_overhead_ratio=`2.457782`
- `narrow_passage` / `CX16-E (No-Substrate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.240078`
- `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.006491`
- `parasol_misc` / `CX16-E (Full)`: success_delta_pp=`0.000`, exp_delta=`-120.000`, mean_time_overhead_ratio=`3.355015`
- `parasol_misc` / `CX16-E (No-Substrate)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.266260`
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