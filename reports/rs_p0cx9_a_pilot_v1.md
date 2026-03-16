# CX9-A Pilot V1

- scope: `calib_hard_v1` dev-only pilot; no test data used
- branch: `CX9-A`
- split root: `data/split/calib_hard_v1`
- train cases: `10`
- val cases: `7`
- cap: `20000`
- chosen params: `{'stride_cells': 5, 'gate_threshold': 0.45, 'neutral_similarity': 0.1, 'mode_strength': 0.24, 'misc_margin': 0.02}`
- inputs sha256: `outputs/rs_p0cx9_a_pilot_v1/inputs_sha256.json`

## Overall vs accepted `CX3-D` on calib_val
- success_delta_pp=`0.000`
- exp_delta=`746.571`
- time_delta_ms=`-312.936`
- mean_time_overhead_ratio=`0.332510`
- path_delta=`0.013`

## Family Breakdown
- `flange`: success_delta_pp=`0.000`, exp_delta=`1.000`, time_overhead_ratio=`0.362599`, prep_time_ms=`11.871`
- `maze`: success_delta_pp=`0.000`, exp_delta=`1863.000`, time_overhead_ratio=`0.145591`, prep_time_ms=`9.135`
- `narrow_passage`: success_delta_pp=`0.000`, exp_delta=`1.000`, time_overhead_ratio=`0.309396`, prep_time_ms=`11.591`
- `parasol_misc`: success_delta_pp=`0.000`, exp_delta=`-366.000`, time_overhead_ratio=`0.909407`, prep_time_ms=`11.562`

## Readout
- result: positive expansion trend exists, but runtime overhead is still above the target threshold