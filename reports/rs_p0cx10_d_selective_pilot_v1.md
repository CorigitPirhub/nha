# CX10-D-Selective Pilot V1

- protocol: locked base sketch from `outputs/rs_p0cx10_d_pilot_v1/chosen.json`; no sketch retuning after public results
- guard training root: `data/benchmark/rs_root_hard_v2/dev` (dev-only; no test/public labels used)
- threshold selection split: `data/split/calib_hard_v1/calib_val.csv`
- teacher chosen json: `outputs/rs_p0cx8_d_hard_pilot_v1/chosen.json`
- base chosen json: `outputs/rs_p0cx10_d_pilot_v1/chosen.json`
- chosen guard params: `{'prob_threshold': 0.55, 'sketch_conf_threshold': 0.22, 'tree_max_depth': 2}`
- val classification metrics: `{'tp': 1, 'fp': 0, 'tn': 5, 'fn': 1, 'applied': 1}`
- output root: `/home/zzy/TrajectoryPlanning/distill/outputs/rs_p0cx10_d_selective_pilot_v1`

## Calib Val vs accepted `CX3-D`
- success_delta_pp=`0.000`
- exp_delta=`-0.429`
- mean_time_overhead_ratio=`-0.022280`
- path_delta=`0.000`

## Calib Family Breakdown
- `flange`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.000000`, apply_rate=`0.000`
- `maze`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.000000`, apply_rate=`0.000`
- `narrow_passage`: success_delta_pp=`0.000`, exp_delta=`-1.500`, mean_time_overhead_ratio=`-0.077979`, apply_rate=`0.500`
- `parasol_misc`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.000000`, apply_rate=`0.000`

## Public Parasol vs `CX3-D`
- `exp3` / `CX10-D (Full)`: success_delta_pp=`-5.556`, exp_delta=`-122.000`, mean_time_overhead_ratio=`-0.011028`, apply_rate=`1.000`
- `exp3` / `CX10-D-Selective`: success_delta_pp=`-5.556`, exp_delta=`-144.111`, mean_time_overhead_ratio=`0.016120`, apply_rate=`0.389`
- `exp3` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-130.333`, mean_time_overhead_ratio=`-0.266459`, apply_rate=`0.000`
- `exp4` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`-123.111`, mean_time_overhead_ratio=`0.386410`, apply_rate=`1.000`
- `exp4` / `CX10-D-Selective`: success_delta_pp=`0.000`, exp_delta=`-145.222`, mean_time_overhead_ratio=`0.149726`, apply_rate=`0.389`
- `exp4` / `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`-137.278`, mean_time_overhead_ratio=`0.025993`, apply_rate=`0.000`

## `exp4` Family Breakdown
- `alpha_puzzle` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.452018`, apply_rate=`1.000`
- `alpha_puzzle` / `CX10-D-Selective`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.000000`, apply_rate=`0.000`
- `bug_trap` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.670019`, apply_rate=`1.000`
- `bug_trap` / `CX10-D-Selective`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.670019`, apply_rate=`1.000`
- `flange` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`-522.800`, mean_time_overhead_ratio=`0.419796`, apply_rate=`1.000`
- `flange` / `CX10-D-Selective`: success_delta_pp=`0.000`, exp_delta=`-522.800`, mean_time_overhead_ratio=`0.111570`, apply_rate=`0.400`
- `maze` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.352910`, apply_rate=`1.000`
- `maze` / `CX10-D-Selective`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.352910`, apply_rate=`1.000`
- `narrow_passage` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`98.750`, mean_time_overhead_ratio=`0.323265`, apply_rate=`1.000`
- `narrow_passage` / `CX10-D-Selective`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.241885`, apply_rate=`0.500`
- `parasol_misc` / `CX10-D (Full)`: success_delta_pp=`0.000`, exp_delta=`0.500`, mean_time_overhead_ratio=`0.344593`, apply_rate=`1.000`
- `parasol_misc` / `CX10-D-Selective`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.000799`, apply_rate=`0.167`

## Standard Support Audit
- `mp`: num_cases=`800`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`
- `csm`: num_cases=`400`, max_abs_field_diff=`0.000000`, mean_abs_field_diff=`0.000000`

## Final Verdict
- selective overall on `exp4`: exp_delta=`-145.222`, mean_time_overhead_ratio=`0.149726`
- full reference on `exp4`: exp_delta=`-123.111`, mean_time_overhead_ratio=`0.386410`
- selective `flange`: exp_delta=`-522.800`
- selective `narrow_passage`: exp_delta=`0.000`
- verdict: FAILED. The guard reduces overhead substantially, but it neither removes the `flange` regression nor preserves the original `narrow_passage` gain, so `CX10-D-Selective` does not clear the rescue gate.