# CX19-B Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow` evaluation; hard-test is consumed when public overall turns positive and `flange` stays non-negative
- chosen params: `{'safe_margin': 0.24, 'boundary_margin': 0.14, 'reverse_need_thr': 0.07, 'oracle_gain_thr': 0.02, 'trap_high_thr': 0.56, 'corridor_low_thr': 0.34, 'support_slack': 0.16, 'max_edges': 2, 'motif_bonus': 0.1, 'family_bonus': 0.08, 'improve_gain': 0.22, 'clearance_w': 0.2, 'corridor_w': 0.26, 'trap_w': 0.36, 'reverse_w': 0.24, 'lateral_w': 0.1, 'forward_w': 0.04, 'heading_w': 0.08, 'stride_cells': 2, 'yaw_stride': 2, 'horizon_steps': 5}`
- output root: `outputs/rs_p0cx19_b_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`0.000`
- exp_delta=`-241.429`
- mean_time_overhead_ratio=`2.049434`

## Calib Family Breakdown
- `flange`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.893546`
- `maze`: exp_delta=`-541.000`, mean_time_overhead_ratio=`1.877026`
- `narrow_passage`: exp_delta=`12.000`, mean_time_overhead_ratio=`1.998035`
- `parasol_misc`: exp_delta=`-91.000`, mean_time_overhead_ratio=`2.825344`

## Public Parasol vs `CX3-D`
- `exp3` / `CX19-B (Full)`: success_delta_pp=`0.000`, exp_delta=`-5.222`, mean_time_overhead_ratio=`2.160682`
- `exp3` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`0.042909`
- `exp4` / `CX19-B (Full)`: success_delta_pp=`0.000`, exp_delta=`-5.222`, mean_time_overhead_ratio=`2.155328`
- `exp4` / `CX19-B (No-Compiler-Graph)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.323686`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.028351`

## Public `exp4` Family Breakdown
- `alpha_puzzle` / `CX19-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`2.106937`
- `alpha_puzzle` / `CX19-B (No-Compiler-Graph)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.370278`
- `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.050884`
- `bug_trap` / `CX19-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.987532`
- `bug_trap` / `CX19-B (No-Compiler-Graph)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.320821`
- `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.219008`
- `flange` / `CX19-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.400`, mean_time_overhead_ratio=`2.128292`
- `flange` / `CX19-B (No-Compiler-Graph)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.325669`
- `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.002614`
- `maze` / `CX19-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.931524`
- `maze` / `CX19-B (No-Compiler-Graph)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.320003`
- `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.030750`
- `narrow_passage` / `CX19-B (Full)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`2.192415`
- `narrow_passage` / `CX19-B (No-Compiler-Graph)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.314450`
- `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.006491`
- `parasol_misc` / `CX19-B (Full)`: success_delta_pp=`0.000`, exp_delta=`-19.833`, mean_time_overhead_ratio=`2.332262`
- `parasol_misc` / `CX19-B (No-Compiler-Graph)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.372966`
- `parasol_misc` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-451.500`, mean_time_overhead_ratio=`0.950310`

## Hard Benchmark vs `CX3-D`
- skipped: public positive ceiling gate did not clear, so hard-test evidence was not consumed.

## Hard Family Breakdown
- skipped: no hard-family rows because hard escalation was not triggered.

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`

## Final Readout
- result: public ceiling gate not cleared under the locked protocol.