# P0-CX8-D Heavy Final Eval V1

- protocol: locked heavy retrospective evaluation; no post-test retuning
- chosen json: `outputs/rs_p0cx8_d_hard_pilot_v1/chosen.json`
- locked heavy params: `{'patch_radius': 5, 'hidden_dim': 96, 'bottleneck_gate': 0.42, 'bundle_conf_thr': 0.5, 'bundle_scale': 0.4, 'learning_rate': 0.001, 'weight_decay': 0.0001, 'epochs': 60, 'batch_size': 128}`
- inputs sha256: `outputs/_tmp_rs_p0cx8_d_heavy_smoke/inputs_sha256.json`

## Hard Benchmark vs accepted `CX3-D`
- `Hybrid A* (RS)`: success_delta_pp=`0.000`, exp_delta=`56.667`, mean_time_overhead_ratio=`-0.013168`, path_delta=`0.000`
- `CX8-D (Heavy)`: success_delta_pp=`0.000`, exp_delta=`-2.667`, mean_time_overhead_ratio=`1.463699`, path_delta=`0.000`

## Reference vs `CX9-A` Final Eval
- `CX9-A (Full)` final-eval reference: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`-0.005238`

## Family Breakdown (Heavy vs `CX3-D`)
- `alpha_puzzle`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`4.310689`
- `bug_trap`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`3.403566`
- `flange`: success_delta_pp=`0.000`, exp_delta=`-5.333`, mean_time_overhead_ratio=`1.469054`
- `maze`: success_delta_pp=`0.000`, exp_delta=`0.000`, mean_time_overhead_ratio=`0.097799`

## Ceiling Reading
- `CX8-D Heavy` does not retain a positive test-side expansion gain, so the strongest dev-side semantic signal does not generalize to the locked hard benchmark.

## Final Verdict
- This evaluation is ceiling-oriented only and does not override the accepted mainline by itself.