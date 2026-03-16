# CX21-C Pilot V1

- protocol: dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; this round intentionally stayed public-first and did not consume hard-test evidence
- chosen params: `{'support_slack': 0.18, 'allowed_bonus': 0.08, 'graph_bonus': 0.1, 'local_refine_bonus': 0.1, 'local_refine_penalty': 0.12, 'macro_bonus': 0.08, 'improve_gain': 0.14, 'max_macros': 3, 'max_graph_nodes': 2, 'min_graph_hits': 4, 'forward_viability_thr': 0.34, 'reverse_required_thr': 0.08, 'trap_high_thr': 0.56, 'escape_affinity_low_thr': -0.02, 'hopeless_viability_thr': 0.1, 'stride_cells': 2, 'yaw_stride': 2, 'horizon_steps': 5}`
- output root: `outputs/rs_p0cx21_c_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`-14.286`
- exp_delta=`-723.857`
- mean_time_overhead_ratio=`4.115335`

## Calib Family Breakdown
- `flange`: exp_delta=`2329.000`, mean_time_overhead_ratio=`2.910012`
- `maze`: exp_delta=`-2449.667`, mean_time_overhead_ratio=`4.511007`
- `narrow_passage`: exp_delta=`173.500`, mean_time_overhead_ratio=`3.309042`
- `parasol_misc`: exp_delta=`-394.000`, mean_time_overhead_ratio=`5.746226`

## Public Parasol vs `CX3-D`
- `exp4` / `CX21-C (Full)`: success_delta_pp=`0.000`, exp_delta=`56.611`, mean_time_overhead_ratio=`3.748104`
- `exp4` / `CX21-C (No-Stable-Graph)`: success_delta_pp=`0.000`, exp_delta=`56.611`, mean_time_overhead_ratio=`3.600651`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.028351`

## Public `exp4` Family Breakdown
- `alpha_puzzle` / `CX21-C (Full)`: success_delta_pp=`0.000`, exp_delta=`-1.000`, mean_time_overhead_ratio=`4.053642`
- `alpha_puzzle` / `CX21-C (No-Stable-Graph)`: success_delta_pp=`0.000`, exp_delta=`-1.000`, mean_time_overhead_ratio=`3.757260`
- `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.050884`
- `bug_trap` / `CX21-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`3.669712`
- `bug_trap` / `CX21-C (No-Stable-Graph)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`3.412308`
- `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.219008`
- `flange` / `CX21-C (Full)`: success_delta_pp=`0.000`, exp_delta=`303.600`, mean_time_overhead_ratio=`3.673700`
- `flange` / `CX21-C (No-Stable-Graph)`: success_delta_pp=`0.000`, exp_delta=`303.600`, mean_time_overhead_ratio=`3.522803`
- `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.002614`
- `maze` / `CX21-C (Full)`: success_delta_pp=`0.000`, exp_delta=`-16.000`, mean_time_overhead_ratio=`4.313402`
- `maze` / `CX21-C (No-Stable-Graph)`: success_delta_pp=`0.000`, exp_delta=`-16.000`, mean_time_overhead_ratio=`4.114654`
- `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.030750`
- `narrow_passage` / `CX21-C (Full)`: success_delta_pp=`0.000`, exp_delta=`39.500`, mean_time_overhead_ratio=`3.773657`
- `narrow_passage` / `CX21-C (No-Stable-Graph)`: success_delta_pp=`0.000`, exp_delta=`39.500`, mean_time_overhead_ratio=`3.633790`
- `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.006491`
- `parasol_misc` / `CX21-C (Full)`: success_delta_pp=`0.000`, exp_delta=`-106.667`, mean_time_overhead_ratio=`4.893121`
- `parasol_misc` / `CX21-C (No-Stable-Graph)`: success_delta_pp=`0.000`, exp_delta=`-106.667`, mean_time_overhead_ratio=`4.743396`
- `parasol_misc` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-451.500`, mean_time_overhead_ratio=`0.950310`

## Hard Benchmark vs `CX3-D`
- skipped: this round intentionally stayed public-first / ordinary-support (`--skip-hard`), so no hard-test evidence was consumed.

## Hard Family Breakdown
- skipped: this round intentionally stayed public-first / ordinary-support (`--skip-hard`), so no hard-test evidence was consumed.

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`

## Final Readout
- result: public ceiling gate cleared.
