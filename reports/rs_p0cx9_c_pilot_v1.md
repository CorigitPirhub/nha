# CX9-C Pilot V1

- scope: `calib_hard_v1` dev-only pilot; no test data used
- branch: `CX9-C`
- split root: `data/split/calib_hard_v1`
- train cases: `10`
- val cases: `7`
- cap: `20000`
- chosen params: `{'stride_cells': 5, 'yaw_clusters': 6, 'gate_threshold': 0.48, 'mode_strength': 0.4, 'hidden_dim': 96, 'learning_rate': 0.0008, 'weight_decay': 0.0003, 'epochs': 75, 'batch_size': 128}`
- inputs sha256: `outputs/rs_p0cx9_c_pilot_v1/inputs_sha256.json`

## Overall vs accepted `CX3-D` on calib_val
- success_delta_pp=`0.000`
- exp_delta=`0.000`
- time_delta_ms=`-1217.661`
- mean_time_overhead_ratio=`0.833537`
- path_delta=`0.000`

## Family Breakdown
- `flange`: success_delta_pp=`0.000`, exp_delta=`0.000`, time_overhead_ratio=`0.523038`, prep_time_ms=`381.640`
- `maze`: success_delta_pp=`0.000`, exp_delta=`0.000`, time_overhead_ratio=`0.487226`, prep_time_ms=`471.659`
- `narrow_passage`: success_delta_pp=`0.000`, exp_delta=`0.000`, time_overhead_ratio=`0.909808`, prep_time_ms=`389.734`
- `parasol_misc`: success_delta_pp=`0.000`, exp_delta=`0.000`, time_overhead_ratio=`2.030427`, prep_time_ms=`399.659`

## Readout
- result: no positive cross-family pilot trend yet under the current implementation