# CX9-B Pilot V1

- scope: `calib_hard_v1` dev-only pilot; no test data used
- branch: `CX9-B`
- split root: `data/split/calib_hard_v1`
- train cases: `10`
- val cases: `7`
- cap: `20000`
- chosen params: `{'top_k': 2, 'gate_threshold': 0.48, 'reach_thr_m': 2.2, 'mode_strength': 0.4}`
- inputs sha256: `outputs/rs_p0cx9_b_pilot_v1/inputs_sha256.json`

## Overall vs accepted `CX3-D` on calib_val
- success_delta_pp=`0.000`
- exp_delta=`-602.429`
- time_delta_ms=`-912.283`
- mean_time_overhead_ratio=`0.493031`
- path_delta=`-0.002`

## Family Breakdown
- `flange`: success_delta_pp=`0.000`, exp_delta=`0.000`, time_overhead_ratio=`0.333862`, prep_time_ms=`0.445`
- `maze`: success_delta_pp=`0.000`, exp_delta=`-1072.333`, time_overhead_ratio=`0.432086`, prep_time_ms=`0.452`
- `narrow_passage`: success_delta_pp=`0.000`, exp_delta=`-306.000`, time_overhead_ratio=`0.485265`, prep_time_ms=`0.442`
- `parasol_misc`: success_delta_pp=`0.000`, exp_delta=`-388.000`, time_overhead_ratio=`0.850567`, prep_time_ms=`0.470`

## Readout
- result: no positive cross-family pilot trend yet under the current implementation