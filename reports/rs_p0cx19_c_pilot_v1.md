# CX19-C Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow` evaluation; hard-test is consumed when public overall turns positive and `flange` stays non-negative
- chosen params: `{'safe_margin': 0.24, 'boundary_margin': 0.14, 'reverse_need_thr': 0.07, 'oracle_gain_thr': 0.02, 'trap_high_thr': 0.56, 'corridor_low_thr': 0.34, 'support_slack': 0.16, 'max_macros': 2, 'max_edges': 2, 'macro_bonus': 0.1, 'motif_bonus': 0.1, 'border_bonus': 0.12, 'grammar_bonus': 0.1, 'review_gain': 0.2, 'clearance_w': 0.2, 'corridor_w': 0.26, 'trap_w': 0.36, 'reverse_w': 0.24, 'lateral_w': 0.1, 'forward_w': 0.04, 'heading_w': 0.08, 'stride_cells': 2, 'yaw_stride': 2, 'horizon_steps': 5}`
- output root: `outputs/rs_p0cx19_c_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`0.000`
- exp_delta=`-241.429`
- mean_time_overhead_ratio=`2.082606`

## Calib Family Breakdown
- `flange`: exp_delta=`0.000`, mean_time_overhead_ratio=`1.906882`
- `maze`: exp_delta=`-541.000`, mean_time_overhead_ratio=`1.890658`
- `narrow_passage`: exp_delta=`12.000`, mean_time_overhead_ratio=`2.057010`
- `parasol_misc`: exp_delta=`-91.000`, mean_time_overhead_ratio=`2.885367`

## Public Parasol vs `CX3-D`
- `exp3` / `CX19-C (Full)`: success_delta_pp=`0.000`, exp_delta=`-1.389`, mean_time_overhead_ratio=`2.185755`
- `exp3` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`0.042909`
- `exp4` / `CX19-C (Full)`: success_delta_pp=`0.000`, exp_delta=`-1.389`, mean_time_overhead_ratio=`2.182987`
- `exp4` / `CX19-C (No-Unified-Graph)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.326443`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.028351`

## Public `exp4` Family Breakdown
- `alpha_puzzle` / `CX19-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`2.011166`
- `alpha_puzzle` / `CX19-C (No-Unified-Graph)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.372500`
- `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.050884`
- `bug_trap` / `CX19-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.882193`
- `bug_trap` / `CX19-C (No-Unified-Graph)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.320522`
- `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.219008`
- `flange` / `CX19-C (Full)`: success_delta_pp=`0.000`, exp_delta=`1.600`, mean_time_overhead_ratio=`2.157465`
- `flange` / `CX19-C (No-Unified-Graph)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.328264`
- `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.002614`
- `maze` / `CX19-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.917860`
- `maze` / `CX19-C (No-Unified-Graph)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.321168`
- `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.030750`
- `narrow_passage` / `CX19-C (Full)`: success_delta_pp=`0.000`, exp_delta=`21.500`, mean_time_overhead_ratio=`2.217756`
- `narrow_passage` / `CX19-C (No-Unified-Graph)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.320962`
- `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.006491`
- `parasol_misc` / `CX19-C (Full)`: success_delta_pp=`0.000`, exp_delta=`-19.833`, mean_time_overhead_ratio=`2.356058`
- `parasol_misc` / `CX19-C (No-Unified-Graph)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.343490`
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