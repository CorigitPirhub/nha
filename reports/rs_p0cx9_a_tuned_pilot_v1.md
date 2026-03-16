# CX9-A Tuned Pilot V1

- scope: `calib_hard_v1` dev-only pilot; no test data used
- branch: `CX9-A`
- split root: `data/split/calib_hard_v1`
- train cases: `10`
- val cases: `7`
- cap: `20000`
- chosen params: `{'stride_cells': 6, 'gate_threshold': 0.48, 'neutral_similarity': 0.12, 'apply_conf_threshold': 0.1, 'local_score_threshold': 0.25, 'mode_strength': 0.22, 'misc_margin': 0.04, 'misc_misc_thr': 0.82, 'misc_open_thr': 0.95, 'misc_bridge_thr': 0.12}`
- inputs sha256: `outputs/rs_p0cx9_a_tuned_pilot_v1/inputs_sha256.json`

## Overall vs accepted `CX3-D` on calib_val
- success_delta_pp=`0.000`
- exp_delta=`814.714`
- time_delta_ms=`92.027`
- mean_time_overhead_ratio=`-0.001933`
- path_delta=`0.013`

## Family Breakdown
- `flange`: success_delta_pp=`0.000`, exp_delta=`2.000`, time_overhead_ratio=`0.074657`, prep_time_ms=`9.133`
- `maze`: success_delta_pp=`0.000`, exp_delta=`1900.333`, time_overhead_ratio=`-0.086878`, prep_time_ms=`6.392`
- `narrow_passage`: success_delta_pp=`0.000`, exp_delta=`0.000`, time_overhead_ratio=`0.040043`, prep_time_ms=`9.037`
- `parasol_misc`: success_delta_pp=`0.000`, exp_delta=`0.000`, time_overhead_ratio=`0.092360`, prep_time_ms=`8.849`

## Readout
- result: positive pilot trend with controlled runtime overhead

## Final Verdict
- `CX9-A` passes all current gates for promotion to the next stage.
- It maintains a positive overall `exp_delta = +814.714`, keeps `success_delta_pp = 0.0`, achieves `mean_time_overhead_ratio = -0.0019 < 0.30`, and removes the `parasol_misc` regression (`exp_delta = 0.0`).
- Therefore `CX9-A / RS-SBM` is promoted to `PASSED TO NEXT STAGE`.
