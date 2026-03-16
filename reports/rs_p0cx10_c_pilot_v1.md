# CX10-C Pilot V1

- protocol: params selected on `data/split/calib_hard_v1` only; public `parasol_narrow` was evaluated after lock-in; no extra test-time tuning
- chosen params: `{'regime_floor': 0.42, 'teacher_conf_floor': 0.52, 'sample_stride': 2, 'similarity_thr': 0.24, 'bottleneck_thr': 0.4, 'misc_margin': 0.04, 'mode_strength': 0.3, 'history_steps': 4, 'persist_steps': 2, 'reverse_steer_frac': 0.12, 'commit_bottleneck_thr': 0.38}`
- output root: `/home/zzy/TrajectoryPlanning/distill/outputs/rs_p0cx10_c_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`-14.286`
- exp_delta=`-343.857`
- mean_time_overhead_ratio=`0.508193`
- path_delta=`-0.106`

## Calib Family Breakdown
- `flange`: success_delta_pp=`0.000`, exp_delta=`-41.000`, mean_time_overhead_ratio=`0.453994`
- `maze`: success_delta_pp=`-33.333`, exp_delta=`-730.667`, mean_time_overhead_ratio=`0.549620`
- `narrow_passage`: success_delta_pp=`0.000`, exp_delta=`-33.000`, mean_time_overhead_ratio=`0.440114`
- `parasol_misc`: success_delta_pp=`0.000`, exp_delta=`-108.000`, mean_time_overhead_ratio=`0.574266`

## Public Parasol vs `CX3-D`
- `exp3` / `CX10-C (Full)`: success_delta_pp=`0.000`, exp_delta=`-7.222`, mean_time_overhead_ratio=`0.530771`
- `exp3` / `CX10-C (No-Phase)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.518966`
- `exp3` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`-0.266459`
- `exp4` / `CX10-C (Full)`: success_delta_pp=`0.000`, exp_delta=`-9.500`, mean_time_overhead_ratio=`1.180549`
- `exp4` / `CX10-C (No-Phase)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.161521`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.025993`

## Public Family Delta vs `CX3-D`
- `exp3` / `alpha_puzzle` / `CX10-C (Full)`: success_delta_pp=`0.000`, exp_delta=`-1.000`, mean_time_overhead_ratio=`0.451385`
- `exp3` / `alpha_puzzle` / `CX10-C (No-Phase)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.348302`
- `exp3` / `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.360698`
- `exp3` / `bug_trap` / `CX10-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.326139`
- `exp3` / `bug_trap` / `CX10-C (No-Phase)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.316040`
- `exp3` / `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.472979`
- `exp3` / `flange` / `CX10-C (Full)`: success_delta_pp=`0.000`, exp_delta=`-5.600`, mean_time_overhead_ratio=`0.581772`
- `exp3` / `flange` / `CX10-C (No-Phase)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.573019`
- `exp3` / `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`67.600`, mean_time_overhead_ratio=`-0.282315`
- `exp3` / `maze` / `CX10-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.429967`
- `exp3` / `maze` / `CX10-C (No-Phase)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.404353`
- `exp3` / `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.357161`
- `exp3` / `narrow_passage` / `CX10-C (Full)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`0.453168`
- `exp3` / `narrow_passage` / `CX10-C (No-Phase)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.448320`
- `exp3` / `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.338468`
- `exp3` / `parasol_misc` / `CX10-C (Full)`: success_delta_pp=`0.000`, exp_delta=`-17.500`, mean_time_overhead_ratio=`0.505981`
- `exp3` / `parasol_misc` / `CX10-C (No-Phase)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.433473`
- `exp3` / `parasol_misc` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-451.500`, mean_time_overhead_ratio=`0.246555`
- `exp4` / `alpha_puzzle` / `CX10-C (Full)`: success_delta_pp=`0.000`, exp_delta=`-1.000`, mean_time_overhead_ratio=`1.186150`
- `exp4` / `alpha_puzzle` / `CX10-C (No-Phase)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.020068`
- `exp4` / `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.006153`
- `exp4` / `bug_trap` / `CX10-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.982769`
- `exp4` / `bug_trap` / `CX10-C (No-Phase)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.966542`
- `exp4` / `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.190049`
- `exp4` / `flange` / `CX10-C (Full)`: success_delta_pp=`0.000`, exp_delta=`-13.800`, mean_time_overhead_ratio=`1.172669`
- `exp4` / `flange` / `CX10-C (No-Phase)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.154809`
- `exp4` / `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.007525`
- `exp4` / `maze` / `CX10-C (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.175073`
- `exp4` / `maze` / `CX10-C (No-Phase)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.129656`
- `exp4` / `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.015034`
- `exp4` / `narrow_passage` / `CX10-C (Full)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`1.190379`
- `exp4` / `narrow_passage` / `CX10-C (No-Phase)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.175623`
- `exp4` / `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`0.001923`
- `exp4` / `parasol_misc` / `CX10-C (Full)`: success_delta_pp=`0.000`, exp_delta=`-17.500`, mean_time_overhead_ratio=`1.238724`
- `exp4` / `parasol_misc` / `CX10-C (No-Phase)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.159718`
- `exp4` / `parasol_misc` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-451.500`, mean_time_overhead_ratio=`0.889685`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`

## Final Readout
- result: candidate regresses relative to accepted `CX3-D` on public parasol and should not advance.