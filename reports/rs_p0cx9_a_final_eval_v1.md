# P0-CX9-A Final Eval V1

- protocol: locked final evaluation from tuned chosen params; no post-test retuning
- chosen json: `outputs/rs_p0cx9_a_tuned_pilot_v1/chosen.json`
- locked params: `{'stride_cells': 6, 'gate_threshold': 0.48, 'neutral_similarity': 0.12, 'apply_conf_threshold': 0.1, 'local_score_threshold': 0.25, 'mode_strength': 0.22, 'misc_margin': 0.04, 'misc_misc_thr': 0.82, 'misc_open_thr': 0.95, 'misc_bridge_thr': 0.12}`
- no-stability params: `{'stride_cells': 6, 'gate_threshold': 0.48, 'neutral_similarity': 0.12, 'apply_conf_threshold': 0.1, 'local_score_threshold': 0.25, 'mode_strength': 0.22, 'misc_margin': -1.0, 'misc_misc_thr': 1.1, 'misc_open_thr': 2.0, 'misc_bridge_thr': 1.0}`
- report table: `paper/tables_rs_root_v1/table_rs_cx9a_final_eval_v1.csv`
- inputs sha256: `outputs/rs_p0cx9_a_final_eval_v1/inputs_sha256.json`

## Hard Benchmark vs accepted `CX3-D`
- `Hybrid A* (RS)`: success_delta_pp=`1.370`, exp_delta=`214.973`, mean_time_overhead_ratio=`-0.062391`, path_delta=`-0.626`
- `CX9-A (Full)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.005238`, path_delta=`0.000`
- `CX9-A (No-Stability)`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.018720`, path_delta=`0.000`

## Family Breakdown (Full / No-Stability)
- `alpha_puzzle`: full_exp_delta=`0.000`, full_over=`-0.057573`, nostability_exp_delta=`0.000`, nostability_over=`-0.063715`
- `bug_trap`: full_exp_delta=`0.000`, full_over=`-0.109019`, nostability_exp_delta=`0.000`, nostability_over=`-0.105803`
- `deadend_labyrinth`: full_exp_delta=`0.000`, full_over=`0.056271`, nostability_exp_delta=`0.000`, nostability_over=`0.035749`
- `flange`: full_exp_delta=`0.000`, full_over=`0.060815`, nostability_exp_delta=`0.000`, nostability_over=`0.024038`
- `maze`: full_exp_delta=`0.000`, full_over=`0.036171`, nostability_exp_delta=`0.000`, nostability_over=`0.024173`
- `narrow_passage`: full_exp_delta=`0.000`, full_over=`0.040683`, nostability_exp_delta=`0.000`, nostability_over=`0.043605`
- `parasol_misc`: full_exp_delta=`0.000`, full_over=`0.202990`, nostability_exp_delta=`0.000`, nostability_over=`0.179064`

## Ordinary Support (`mp/csm`)
- `mp`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.060484`
- `csm`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.034239`

## Final Verdict
- `CX9-A` does not hold under locked test evaluation strongly enough for promotion; keep the current accepted mainline.