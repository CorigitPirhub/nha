# P0-CX9-A Final Eval V1

- protocol: locked final evaluation from tuned chosen params; no post-test retuning
- chosen json: `outputs/rs_p0cx9_a_tuned_pilot_v1/chosen.json`
- locked params: `{'stride_cells': 6, 'gate_threshold': 0.48, 'neutral_similarity': 0.12, 'apply_conf_threshold': 0.1, 'local_score_threshold': 0.25, 'mode_strength': 0.22, 'misc_margin': 0.04, 'misc_misc_thr': 0.82, 'misc_open_thr': 0.95, 'misc_bridge_thr': 0.12}`
- report table: `paper/tables_rs_root_v1/_tmp_rs_cx9a_final_smoke.csv`
- inputs sha256: `outputs/_tmp_rs_p0cx9_a_final_smoke/inputs_sha256.json`

## Hard Benchmark vs accepted `CX3-D`
- `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`56.667`, mean_time_overhead_ratio=`-0.009451`, path_delta=`0.000`
- `CX9-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.079358`, path_delta=`0.000`
- `CX9-A (No-Stability)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.037825`, path_delta=`0.000`

## Family Breakdown (Full / No-Stability)
- `alpha_puzzle`: full_exp_delta=`0.000`, full_over=`1.824251`, nostability_exp_delta=`0.000`, nostability_over=`1.737764`
- `bug_trap`: full_exp_delta=`0.000`, full_over=`3.780784`, nostability_exp_delta=`0.000`, nostability_over=`3.772340`
- `flange`: full_exp_delta=`0.000`, full_over=`0.076502`, nostability_exp_delta=`0.000`, nostability_over=`0.034691`
- `maze`: full_exp_delta=`0.000`, full_over=`0.222459`, nostability_exp_delta=`0.000`, nostability_over=`0.233900`

## Ordinary Support (`mp/csm`)

## Final Verdict
- `CX9-A` does not hold under locked test evaluation strongly enough for promotion; keep the current accepted mainline.