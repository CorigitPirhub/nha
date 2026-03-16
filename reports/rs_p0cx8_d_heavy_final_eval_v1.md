# P0-CX8-D Heavy Final Eval V1

- protocol: locked heavy retrospective evaluation; no post-test retuning
- chosen json: `outputs/rs_p0cx8_d_hard_pilot_v1/chosen.json`
- locked heavy params: `{'patch_radius': 5, 'hidden_dim': 96, 'bottleneck_gate': 0.42, 'bundle_conf_thr': 0.5, 'bundle_scale': 0.4, 'learning_rate': 0.001, 'weight_decay': 0.0001, 'epochs': 60, 'batch_size': 128}`
- inputs sha256: `outputs/rs_p0cx8_d_heavy_final_eval_v1/inputs_sha256.json`

## Hard Benchmark vs accepted `CX3-D`
- `Hybrid A* (RS)`: success_delta_pp=`1.370`, exp_delta=`214.973`, mean_time_overhead_ratio=`-0.031956`, path_delta=`-0.626`
- `CX8-D (Heavy)`: success_delta_pp=`0.000`, exp_delta=`58.575`, mean_time_overhead_ratio=`1.285604`, path_delta=`0.023`

## Reference vs `CX9-A` Final Eval
- `CX9-A (Full)` final-eval reference: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.005238`

## Family Breakdown (Heavy vs `CX3-D`)
- `alpha_puzzle`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.295552`
- `bug_trap`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.046292`
- `deadend_labyrinth`: success_delta_pp=`0.000`, exp_delta=`62.200`, mean_time_overhead_ratio=`3.579099`
- `flange`: success_delta_pp=`0.000`, exp_delta=`-1.231`, mean_time_overhead_ratio=`1.703702`
- `maze`: success_delta_pp=`0.000`, exp_delta=`338.545`, mean_time_overhead_ratio=`0.451306`
- `narrow_passage`: success_delta_pp=`0.000`, exp_delta=`-4.154`, mean_time_overhead_ratio=`1.381612`
- `parasol_misc`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`1.337572`

## Ceiling Reading
- `CX8-D Heavy` generalizes positively on test, which means the ceiling of semantic intervention remains real but computationally expensive.

## Final Verdict
- This evaluation is ceiling-oriented only and does not override the accepted mainline by itself.