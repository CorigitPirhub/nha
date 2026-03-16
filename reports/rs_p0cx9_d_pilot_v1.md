# CX9-D Pilot V1

- scope: `calib_hard_v1` dev-only pilot; no test data used
- branch: `CX9-D`
- split root: `data/split/calib_hard_v1`
- train cases: `10`
- val cases: `7`
- cap: `20000`
- chosen params: `{'top_k': 2, 'gate_threshold': 0.42, 'window_radius_m': 2.0, 'mode_strength': 0.3, 'neutral_similarity': 0.1}`
- inputs sha256: `outputs/rs_p0cx9_d_pilot_v1/inputs_sha256.json`

## Overall vs accepted `CX3-D` on calib_val
- success_delta_pp=`0.000`
- exp_delta=`-2.143`
- time_delta_ms=`-745.224`
- mean_time_overhead_ratio=`0.338098`
- path_delta=`0.000`

## Family Breakdown
- `flange`: success_delta_pp=`0.000`, exp_delta=`0.000`, time_overhead_ratio=`0.359393`, prep_time_ms=`0.444`
- `maze`: success_delta_pp=`0.000`, exp_delta=`-4.000`, time_overhead_ratio=`0.333736`, prep_time_ms=`0.517`
- `narrow_passage`: success_delta_pp=`0.000`, exp_delta=`0.000`, time_overhead_ratio=`0.328176`, prep_time_ms=`0.515`
- `parasol_misc`: success_delta_pp=`0.000`, exp_delta=`-3.000`, time_overhead_ratio=`0.349734`, prep_time_ms=`0.513`

## Readout
- result: no positive cross-family pilot trend yet under the current implementation