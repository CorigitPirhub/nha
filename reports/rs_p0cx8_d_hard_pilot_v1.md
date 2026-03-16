# CX8-D Hard Pilot V1

- scope: `calib_hard_v1` dev-only pilot; no test data used
- branch: `CX8-D`
- split root: `data/split/calib_hard_v1`
- train cases: `10`
- val cases: `7`
- cap: `20000`
- chosen params: `{'patch_radius': 5, 'hidden_dim': 96, 'bottleneck_gate': 0.42, 'bundle_conf_thr': 0.5, 'bundle_scale': 0.4, 'learning_rate': 0.001, 'weight_decay': 0.0001, 'epochs': 60, 'batch_size': 128}`
- train/val samples: `139`/`151`
- inputs sha256: `outputs/rs_p0cx8_d_hard_pilot_v1/inputs_sha256.json`

## Overall vs accepted `CX3-D` on calib_val
- success_delta_pp=`0.000`
- exp_delta=`989.714`
- time_delta_ms=`-1488.465`
- mean_time_overhead_ratio=`1.328295`
- path_delta=`0.027`

## Family Breakdown
- `flange`: success_delta_pp=`0.000`, exp_delta=`1602.000`, time_overhead_ratio=`0.525007`
- `maze`: success_delta_pp=`0.000`, exp_delta=`1776.000`, time_overhead_ratio=`0.467492`
- `narrow_passage`: success_delta_pp=`0.000`, exp_delta=`-0.500`, time_overhead_ratio=`1.961916`
- `parasol_misc`: success_delta_pp=`0.000`, exp_delta=`-1.000`, time_overhead_ratio=`3.446754`

## Readout
- result: positive expansion trend exists, but runtime overhead is still above the target threshold