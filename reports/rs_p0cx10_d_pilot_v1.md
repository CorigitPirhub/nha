# CX10-D Pilot V1

- protocol: params selected on `data/split/calib_hard_v1` only; public `parasol_narrow` was evaluated after lock-in; no extra test-time tuning
- chosen params: `{'regime_floor': 0.38, 'teacher_conf_floor': 0.48, 'sample_stride': 1, 'top_k_windows': 3, 'gate_threshold': 0.38, 'macro_radius_m': 3.4, 'commit_radius_m': 1.6, 'similarity_thr': 0.2, 'bottleneck_thr': 0.36, 'scene_similarity_thr': 0.16, 'misc_margin': 0.06, 'mode_strength': 0.25, 'use_scene_template': True}`
- output root: `/home/zzy/TrajectoryPlanning/distill/outputs/rs_p0cx10_d_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`0.000`
- exp_delta=`-20.143`
- mean_time_overhead_ratio=`-0.112479`
- path_delta=`-0.086`

## Calib Family Breakdown
- `flange`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.104060`
- `maze`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.125570`
- `narrow_passage`: success_delta_pp=`0.000`, exp_delta=`-70.500`, mean_time_overhead_ratio=`-0.102518`
- `parasol_misc`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.101547`

## Public Parasol vs `CX3-D`
- `exp3` / `CX10-D (Full)`: success_delta_pp=`-5.556`, exp_delta=`-122.000`, mean_time_overhead_ratio=`-0.011028`
- `exp3` / `CX10-D (No-Template)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.066167`
- `exp3` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`-0.266459`
- `exp4` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`-123.111`, mean_time_overhead_ratio=`0.386410`
- `exp4` / `CX10-D (No-Template)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.339740`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.025993`

## Public Family Delta vs `CX3-D`
- `exp3` / `alpha_puzzle` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.032197`
- `exp3` / `alpha_puzzle` / `CX10-D (No-Template)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.059049`
- `exp3` / `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.360698`
- `exp3` / `bug_trap` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.090718`
- `exp3` / `bug_trap` / `CX10-D (No-Template)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.059786`
- `exp3` / `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.472979`
- `exp3` / `flange` / `CX10-D (Full)`: success_delta_pp=`-20.000`, exp_delta=`-518.800`, mean_time_overhead_ratio=`0.071214`
- `exp3` / `flange` / `CX10-D (No-Template)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.031373`
- `exp3` / `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`67.600`, mean_time_overhead_ratio=`-0.282315`
- `exp3` / `maze` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.113370`
- `exp3` / `maze` / `CX10-D (No-Template)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.118671`
- `exp3` / `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.357161`
- `exp3` / `narrow_passage` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`98.750`, mean_time_overhead_ratio=`-0.126480`
- `exp3` / `narrow_passage` / `CX10-D (No-Template)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.113671`
- `exp3` / `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.338468`
- `exp3` / `parasol_misc` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.500`, mean_time_overhead_ratio=`-0.105755`
- `exp3` / `parasol_misc` / `CX10-D (No-Template)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.112988`
- `exp3` / `parasol_misc` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-451.500`, mean_time_overhead_ratio=`0.246555`
- `exp4` / `alpha_puzzle` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.452018`
- `exp4` / `alpha_puzzle` / `CX10-D (No-Template)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.417793`
- `exp4` / `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.006153`
- `exp4` / `bug_trap` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.670019`
- `exp4` / `bug_trap` / `CX10-D (No-Template)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.596820`
- `exp4` / `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.190049`
- `exp4` / `flange` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`-522.800`, mean_time_overhead_ratio=`0.419796`
- `exp4` / `flange` / `CX10-D (No-Template)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.343277`
- `exp4` / `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.007525`
- `exp4` / `maze` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.352910`
- `exp4` / `maze` / `CX10-D (No-Template)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.340209`
- `exp4` / `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.015034`
- `exp4` / `narrow_passage` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`98.750`, mean_time_overhead_ratio=`0.323265`
- `exp4` / `narrow_passage` / `CX10-D (No-Template)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.332528`
- `exp4` / `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`0.001923`
- `exp4` / `parasol_misc` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.500`, mean_time_overhead_ratio=`0.344593`
- `exp4` / `parasol_misc` / `CX10-D (No-Template)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.339118`
- `exp4` / `parasol_misc` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-451.500`, mean_time_overhead_ratio=`0.889685`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`

## Final Readout
- result: candidate regresses relative to accepted `CX3-D` on public parasol and should not advance.