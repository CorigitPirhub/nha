# CX8-D Optimized Hard Pilot V1

- scope: `calib_hard_v1` dev-only pilot; no test data used
- branch: `CX8-D`
- split root: `data/split/calib_hard_v1`
- train cases: `10`
- val cases: `7`
- cap: `20000`
- chosen params: `{'patch_radius': 0, 'hidden_dim': 40, 'bottleneck_gate': 0.5, 'activation_gate': 0.7, 'bundle_conf_thr': 0.58, 'bundle_scale': 0.34, 'learning_rate': 0.0008, 'weight_decay': 0.0001, 'epochs': 50, 'batch_size': 128}`
- train/val samples: `139`/`151`
- inputs sha256: `outputs/rs_p0cx8_d_optimized_hard_pilot_v1/inputs_sha256.json`

## Overall vs accepted `CX3-D` on calib_val
- success_delta_pp=`0.000`
- exp_delta=`0.000`
- time_delta_ms=`-279.950`
- mean_time_overhead_ratio=`0.163009`
- path_delta=`0.000`

## Family Breakdown
- `flange`: success_delta_pp=`0.000`, exp_delta=`0.000`, time_overhead_ratio=`0.129286`
- `maze`: success_delta_pp=`0.000`, exp_delta=`0.000`, time_overhead_ratio=`0.190591`
- `narrow_passage`: success_delta_pp=`0.000`, exp_delta=`0.000`, time_overhead_ratio=`0.140663`
- `parasol_misc`: success_delta_pp=`0.000`, exp_delta=`0.000`, time_overhead_ratio=`0.158674`


## Pareto Comparison
- previous heavy `CX8-D` pilot (`reports/rs_p0cx8_d_hard_pilot_v1.md`): `exp_delta=+989.714`, `mean_time_overhead_ratio=1.3283`.
- current lightweight optimized pilot: `exp_delta=0.000`, `mean_time_overhead_ratio=0.1630`.
- reading: the lightweight refactor recovers a large part of the runtime overhead, but the positive bundle-arbitration gain collapses to parity with accepted `CX3-D`.
## Readout
- result: no positive cross-family pilot trend yet under the current implementation