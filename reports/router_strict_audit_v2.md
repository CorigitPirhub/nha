# Router Strict Audit Report (Phase27, v2)

## Protocol
- Strict: select/search only on `calib_train/calib_val`; `test` is used once for final evaluation.
- Legacy (diagnostic): allows `test`-set tuning in Phase-8 (conformal/probe). **Not** valid for main claims.

## Strict Results
- Phase9 pooled mean ΔJ (P5 - router): `-0.130400`
- Phase9 pooled 95% CI: `[-0.131355, -0.129469]`
- Phase9 p_boot(gt0): `1.000000e+00`
- Phase13 mean J-improve vs strongest baseline: `-0.841%`
- Phase22 mean J-improve vs best direct baseline: `-0.852%` (best direct=`cdt_worstcase_j_v1`)

## Gate Summary (Strict)
- `phase9_gain_significant`: `False`
- `phase13_sota_significant`: `False`
- `phase22_main_result_significant`: `False`

## Notes
- This strict bundle uses the frozen protocol \(\alpha=0.05\) and counts probe runtime in latency \(T\) for probe-based policies; routing uses predicted cost \(\hat c(x)\) (no oracle per-sample `c`) and excludes dataset-ID features.
- If strict gates fail, main paper claims must be reframed to match strict evidence.
- This report is the single source of truth for strict vs legacy audit status.
