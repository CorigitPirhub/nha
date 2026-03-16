# CX10-A Pilot V1

- protocol: params selected on `data/split/calib_hard_v1` only; public `parasol_narrow` was evaluated after lock-in; no extra test-time tuning
- chosen params: `{'regime_floor': 0.4, 'teacher_conf_floor': 0.5, 'sample_stride': 1, 'similarity_thr': 0.24, 'bottleneck_thr': 0.4, 'misc_margin': 0.04, 'mode_strength': 0.26, 'support_slack': 0.0, 'allow_reverse_low_escape': False}`
- output root: `/home/zzy/TrajectoryPlanning/distill/outputs/rs_p0cx10_a_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`0.000`
- exp_delta=`0.000`
- mean_time_overhead_ratio=`0.446955`
- path_delta=`0.000`

## Calib Family Breakdown
- `flange`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.446963`
- `maze`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.462100`
- `narrow_passage`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.433839`
- `parasol_misc`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.427748`

## Public Parasol vs `CX3-D`
- `exp3` / `CX10-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.161046`
- `exp3` / `CX10-A (No-Abstain)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.075625`
- `exp3` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`-0.045547`
- `exp4` / `CX10-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.188354`
- `exp4` / `CX10-A (No-Abstain)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.184519`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.015989`

## Public Family Delta vs `CX3-D`
- `exp3` / `alpha_puzzle` / `CX10-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`2.021401`
- `exp3` / `alpha_puzzle` / `CX10-A (No-Abstain)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`2.008376`
- `exp3` / `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.026698`
- `exp3` / `bug_trap` / `CX10-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.871889`
- `exp3` / `bug_trap` / `CX10-A (No-Abstain)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.861687`
- `exp3` / `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.178886`
- `exp3` / `flange` / `CX10-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.522822`
- `exp3` / `flange` / `CX10-A (No-Abstain)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.364463`
- `exp3` / `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`67.600`, mean_time_overhead_ratio=`-0.006443`
- `exp3` / `maze` / `CX10-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.418339`
- `exp3` / `maze` / `CX10-A (No-Abstain)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.413121`
- `exp3` / `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.339882`
- `exp3` / `narrow_passage` / `CX10-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.742919`
- `exp3` / `narrow_passage` / `CX10-A (No-Abstain)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.744050`
- `exp3` / `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.203532`
- `exp3` / `parasol_misc` / `CX10-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.690349`
- `exp3` / `parasol_misc` / `CX10-A (No-Abstain)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.690998`
- `exp3` / `parasol_misc` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-451.500`, mean_time_overhead_ratio=`0.488801`
- `exp4` / `alpha_puzzle` / `CX10-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.088516`
- `exp4` / `alpha_puzzle` / `CX10-A (No-Abstain)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.080495`
- `exp4` / `alpha_puzzle` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.034622`
- `exp4` / `bug_trap` / `CX10-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.960562`
- `exp4` / `bug_trap` / `CX10-A (No-Abstain)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.946384`
- `exp4` / `bug_trap` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.233480`
- `exp4` / `flange` / `CX10-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.184082`
- `exp4` / `flange` / `CX10-A (No-Abstain)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.171442`
- `exp4` / `flange` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`42.600`, mean_time_overhead_ratio=`-0.017768`
- `exp4` / `maze` / `CX10-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.117664`
- `exp4` / `maze` / `CX10-A (No-Abstain)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.095839`
- `exp4` / `maze` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`1.000`, mean_time_overhead_ratio=`-0.052645`
- `exp4` / `narrow_passage` / `CX10-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.198643`
- `exp4` / `narrow_passage` / `CX10-A (No-Abstain)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.207347`
- `exp4` / `narrow_passage` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`5.750`, mean_time_overhead_ratio=`-0.007111`
- `exp4` / `parasol_misc` / `CX10-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.177815`
- `exp4` / `parasol_misc` / `CX10-A (No-Abstain)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.224661`
- `exp4` / `parasol_misc` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-451.500`, mean_time_overhead_ratio=`0.878363`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`

## Final Readout
- result: candidate is effectively tied with accepted `CX3-D` on public parasol and does not advance the frontier.