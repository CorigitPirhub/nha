# CX10-B Pilot V1

- protocol: params selected on `data/split/calib_hard_v1` only; public `parasol_narrow` was evaluated after lock-in; no extra test-time tuning
- chosen params: `{'regime_floor': 0.42, 'teacher_conf_floor': 0.52, 'sample_stride': 2, 'top_k_windows': 2, 'gate_threshold': 0.42, 'pre_radius_m': 2.8, 'commit_radius_m': 1.2, 'similarity_thr': 0.24, 'bottleneck_thr': 0.4, 'misc_margin': 0.04, 'mode_strength': 0.3, 'enable_setup': True}`
- output root: `/home/zzy/TrajectoryPlanning/distill/outputs/rs_p0cx10_b_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`0.000`
- exp_delta=`0.000`
- mean_time_overhead_ratio=`-0.131064`
- path_delta=`0.000`

## Calib Family Breakdown
- `flange`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.121703`
- `maze`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.136295`
- `narrow_passage`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.132207`
- `parasol_misc`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.122447`

## Public Parasol vs `CX3-D`
- `exp3` / `CX10-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.063095`
- `exp3` / `CX10-B (No-Setup)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.058274`
- `exp3` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`-0.266459`
- `exp4` / `CX10-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.331174`
- `exp4` / `CX10-B (No-Setup)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.327537`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.025993`

## Public Family Delta vs `CX3-D`
- `exp3` / `alpha_puzzle` / `CX10-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.070312`
- `exp3` / `alpha_puzzle` / `CX10-B (No-Setup)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.080203`
- `exp3` / `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.360698`
- `exp3` / `bug_trap` / `CX10-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.015956`
- `exp3` / `bug_trap` / `CX10-B (No-Setup)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.022932`
- `exp3` / `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.472979`
- `exp3` / `flange` / `CX10-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.024754`
- `exp3` / `flange` / `CX10-B (No-Setup)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.019861`
- `exp3` / `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`67.600`, mean_time_overhead_ratio=`-0.282315`
- `exp3` / `maze` / `CX10-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.120740`
- `exp3` / `maze` / `CX10-B (No-Setup)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.126029`
- `exp3` / `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.357161`
- `exp3` / `narrow_passage` / `CX10-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.116068`
- `exp3` / `narrow_passage` / `CX10-B (No-Setup)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.110504`
- `exp3` / `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.338468`
- `exp3` / `parasol_misc` / `CX10-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.111172`
- `exp3` / `parasol_misc` / `CX10-B (No-Setup)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.110185`
- `exp3` / `parasol_misc` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-451.500`, mean_time_overhead_ratio=`0.246555`
- `exp4` / `alpha_puzzle` / `CX10-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.411009`
- `exp4` / `alpha_puzzle` / `CX10-B (No-Setup)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.353811`
- `exp4` / `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.006153`
- `exp4` / `bug_trap` / `CX10-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.452344`
- `exp4` / `bug_trap` / `CX10-B (No-Setup)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.440762`
- `exp4` / `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.190049`
- `exp4` / `flange` / `CX10-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.322823`
- `exp4` / `flange` / `CX10-B (No-Setup)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.323619`
- `exp4` / `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.007525`
- `exp4` / `maze` / `CX10-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.351151`
- `exp4` / `maze` / `CX10-B (No-Setup)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.350064`
- `exp4` / `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.015034`
- `exp4` / `narrow_passage` / `CX10-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.342085`
- `exp4` / `narrow_passage` / `CX10-B (No-Setup)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.333060`
- `exp4` / `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`0.001923`
- `exp4` / `parasol_misc` / `CX10-B (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.385787`
- `exp4` / `parasol_misc` / `CX10-B (No-Setup)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.348665`
- `exp4` / `parasol_misc` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-451.500`, mean_time_overhead_ratio=`0.889685`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`

## Final Readout
- result: candidate is effectively tied with accepted `CX3-D` on public parasol and does not advance the frontier.