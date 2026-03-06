# Router Validity Audit (V3) — Fullscan

- Date: `2026-03-05`
- Strict bundle: `outputs/final_v6_strict_rerun1`
- Legacy bundle: `outputs/final_v2`

## 1) Dataset split leakage (overlap) checks
- `data/router_phase9_public_v1` pass: `True` overlap: `{'train_x_calib': 0, 'train_x_test': 0, 'calib_x_test': 0}`
- `data/router_mixed_v1` pass: `True` overlap: `{'train_x_calib': 0, 'train_x_test': 0, 'calib_x_test': 0}`

## 2) Metrics reproducibility from artifacts (not hand-written)
- Legacy Phase9 (route-only) exact-match: `True` absdiff_mean=0.000e+00
- Strict Phase9 (probe-in-T) exact-match: `True` absdiff_mean=0.000e+00

- Legacy Phase13 (probe ignored in J) close-match: `True` absdiff_seed_mean=0.000e+00
- Strict Phase13 (probe-in-T) close-match: `True` absdiff_seed_mean=0.000e+00

- Strict Phase22 close-match: `True` absdiff_mean_pct=0.000e+00

## 3) Parquet SHA256 binding (overwrite detection)
- Strict `phase9/common/risk` sha256 record ok: `True` (no_diff)
- Strict `phase9/router_eval` sha256 record ok: `True` (no_diff)
- Strict `phase13` sha256 record ok: `True` (no_diff)
- Strict `phase22` sha256 record ok: `True` (no_diff)

## 4) Workspace drift (bundle vs live outputs)
- Drift detected: `1` mismatches.
  - `outputs/router_phase9_bench_v1/common/router_counterfactual_test.parquet` sha256_live=`75783e4054` sha256_frozen=`55258569d2`

