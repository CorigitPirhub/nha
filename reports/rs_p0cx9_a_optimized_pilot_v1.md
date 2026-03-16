# CX9-A Optimized Pilot V1

- scope: `calib_hard_v1` dev-only pilot; no test data used
- branch: `CX9-A`
- split root: `data/split/calib_hard_v1`
- train cases: `10`
- val cases: `7`
- cap: `20000`
- chosen params: `{'top_k': 2, 'gate_threshold': 0.5, 'conf_threshold': 0.18, 'apply_conf_threshold': 0.18, 'local_score_threshold': 0.42, 'region_radius_m': 1.3, 'mode_strength': 0.16, 'misc_margin': 0.06}`
- inputs sha256: `outputs/rs_p0cx9_a_optimized_pilot_v1/inputs_sha256.json`

## Overall vs accepted `CX3-D` on calib_val
- success_delta_pp=`0.000`
- exp_delta=`-310.143`
- time_delta_ms=`-113.630`
- mean_time_overhead_ratio=`0.064810`
- path_delta=`0.238`

## Family Breakdown
- `flange`: success_delta_pp=`0.000`, exp_delta=`1643.000`, time_overhead_ratio=`-0.121573`, prep_time_ms=`0.427`
- `maze`: success_delta_pp=`0.000`, exp_delta=`-1357.000`, time_overhead_ratio=`0.147056`, prep_time_ms=`0.507`
- `narrow_passage`: success_delta_pp=`0.000`, exp_delta=`301.500`, time_overhead_ratio=`-0.131855`, prep_time_ms=`0.517`
- `parasol_misc`: success_delta_pp=`0.000`, exp_delta=`-346.000`, time_overhead_ratio=`0.397783`, prep_time_ms=`0.536`

## Readout
- result: no positive cross-family pilot trend yet under the current implementation

## Final Verdict
- `CX9-A` passes the efficiency gate (`mean_time_overhead_ratio = 0.0648 < 0.30`) but fails the effect and stability gates.
- Its overall `exp_delta` remains negative (`-310.143`), and `parasol_misc` still regresses (`exp_delta = -346.0`).
- Therefore the `CX9-A` sprint does not justify promotion to the next evaluation stage.
