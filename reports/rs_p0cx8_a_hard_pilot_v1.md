# CX8-A Hard Pilot V1

- scope: `calib_hard_v1` dev-only pilot; no test data used
- branch: `CX8-A`
- split root: `data/split/calib_hard_v1`
- train cases: `10`
- val cases: `7`
- cap: `20000`
- chosen params: `{'patch_radius': 5, 'hidden_dim': 96, 'prior_scale': 0.45, 'learning_rate': 0.001, 'weight_decay': 0.0001, 'epochs': 60, 'batch_size': 128}`
- train/val samples: `519`/`458`
- inputs sha256: `outputs/rs_p0cx8_a_hard_pilot_v1/inputs_sha256.json`

## Overall vs accepted `CX3-D` on calib_val
- success_delta_pp=`0.000`
- exp_delta=`-421.000`
- time_delta_ms=`-8674.071`
- mean_time_overhead_ratio=`4.035041`
- path_delta=`0.179`

## Family Breakdown
- `flange`: success_delta_pp=`0.000`, exp_delta=`1681.000`, time_overhead_ratio=`2.986730`
- `maze`: success_delta_pp=`0.000`, exp_delta=`-1424.667`, time_overhead_ratio=`4.130876`
- `narrow_passage`: success_delta_pp=`0.000`, exp_delta=`8.500`, time_overhead_ratio=`3.650961`
- `parasol_misc`: success_delta_pp=`0.000`, exp_delta=`-371.000`, time_overhead_ratio=`5.564008`

## Readout
- result: no positive cross-family pilot trend yet under the current implementation