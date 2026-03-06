# Router Validity Audit (V2) — Risk Fix + Strict Rerun

Date: 2026-03-05  
Scope: **Dual-Path Router** strict mainline (Phase9→Phase13→Phase22) after resolving all blockers in `reports/router_validity_audit_v1.md`.

This V2 audit is **artifact-driven** and answers two questions:
1) Have we removed the remaining threats to validity (risk/latency semantics, oracle leakage, dataset-ID memorization, bundle drift)?  
2) After fixing them, do the strict main conclusions still hold?

---

## 0. Executive Summary (What changed vs V1)

All V1 “major threats” are addressed in code and re-verified by rerunning the strict chain into a new bundle:
- New strict outputs:
  - Phase9: `outputs/router_phase9_bench_v7_strict_alpha05_probeT_noleak/stats.json`
  - Phase13: `outputs/router_phase13_sota_v5_strict_alpha05_probeT_noleak/stats.json`
  - Phase22: `outputs/router_phase22_direct_baselines_v5_strict_alpha05_probeT_noleak/stats.json`
- New strict single-source summary:
  - `reports/router_strict_audit_v2.md`
- New hash-tracked bundle (no snapshot drift):
  - `outputs/final_v5_strict/manifest.json`

**Result:** Under the corrected strict semantics (α=0.05, probe runtime counted in T, no oracle cost feature, no dataset-ID features), the previous “P6 improves over P5” strict claim does **not** hold.

---

## 1. Threats to Validity — Fixes and Evidence

### 1.1 Risk budget mismatch (α) vs frozen protocol
**V1 issue:** strict Phase9 instantiation used `strict_violation_target≈0.20` while protocol is α=0.05.

**Fix:** strict targets are now aligned to α=0.05 across the strict chain.
- Phase9 strict config records:
  - `phase8_strict_violation_target = 0.05`
  - `phase8_strict_ci_upper_target = 0.05`
  - see `outputs/router_phase9_bench_v7_strict_alpha05_probeT_noleak/stats.json` → `router_eval_config`.
- Per-seed P5 (conformal) complies on test (example seed=7):
  - `violation_rate = 0.031386`, `ci95_upper = 0.037991`
  - see `outputs/router_phase9_bench_v7_strict_alpha05_probeT_noleak/router_eval/seeds/seed_7/mixed/conformal_strict_v2/policy_metrics.json`.

### 1.2 Probe compute not counted in objective J
**V1 issue:** Phase9/13/22 computed `J` from `T_fast_ms/T_slow_ms` only; `probe_runtime_ms` was tracked but excluded.

**Fix:** For probe-based policies, `probe_runtime_ms` is now included in `T` inside `J` in:
- `scripts/run_router_phase9_bench.py:_compute_benchmark_metrics`
- `scripts/run_router_phase13_sota.py:_eval_policy`
- `scripts/run_router_phase22_direct_baselines.py:_eval_policy`

**Magnitude:** On Phase9 test, probe overhead is non-negligible:
- mean `probe_runtime_ms` = `0.892 ms`, median = `1.148 ms`  
  (`outputs/router_phase9_bench_v7_strict_alpha05_probeT_noleak/router_eval/common/probe_features_test.parquet`)
- In normalized objective units, mean probe overhead is ~`0.1301`:
  - measured as `E[probe_runtime_ms/T_ref] ≈ 0.130095` across seeds (see Section 2.2 below).

### 1.3 Oracle feature leakage: per-sample cost `c = T_slow - T_fast`
**V1 issue:** strict routing used oracle `c` (counterfactual-derived) in scoring/selection (and optionally as probe feature).

**Fix:** strict routing never uses oracle per-sample `c` at decision time.
- Phase8 strict now learns a **deployable** cost proxy `c_hat(x)` on `calib_train` using only static features:
  - numeric: `line_block_ratio, local_occ_ratio, global_occ_ratio, distance_ratio, complexity_score, los_clear`
  - categorical: `difficulty`
  - see `scripts/run_router_phase8_strict.py:_predict_cost_c_hat` and the emitted metadata:
    - `.../conformal_strict_v2/policy_metrics.json` → `cost_proxy.name = c_hat_gbr_static_v1`
    - `.../conformal_strict_v2/test_decisions.parquet` includes `c_hat_ms`/`c_hat_norm` (traceability).
- Probe selection no longer has any oracle-assisted fallback:
  - oracle-assisted branches removed; `selected_policy.oracle_assist_used = false` in probe artifacts.

### 1.4 Dataset-ID memorization / “lucky hit” risk (map_id/scenario/source_dataset)
**V1 issue:** Phase8 strict used one-hot categorical identifiers (`map_id/scenario/source_dataset`) which can inflate gains via ID memorization.

**Fix:** dataset identifiers and split-derived flags are removed from strict model inputs.
- `scripts/run_router_phase8_strict.py`:
  - conformal: `_build_conformal_xy` uses only `difficulty` as categorical
  - probe: `_build_probe_xy` uses only `difficulty` as categorical
- Core method defaults updated to match:
  - `utils/router_method_core.py:{ConformalStageConfig,ProbeFlipStageConfig}` now use `feature_cat=('difficulty',)` and drop `ood_family`.

### 1.5 Bundle snapshot drift
**V1 issue:** `outputs/final_v4_strict/manifest.json` reported a hash mismatch for `docs/neurips_method_v1.md` after repo changes.

**Fix:** new strict bundle is rebuilt and hash-tracked end-to-end:
- `outputs/final_v5_strict/manifest.json` records fresh hashes for `docs/router_protocol_v1.md` and `docs/neurips_method_v1.md`.

---

## 2. Post-fix Strict Results (Does the main conclusion still hold?)

### 2.1 Phase9 (public cross-benchmark): P6 vs P5
From `outputs/router_phase9_bench_v7_strict_alpha05_probeT_noleak/stats.json`:
- pooled mean ΔJ (P5 − router): `-0.130400`
- pooled 95% CI: `[-0.131355, -0.129469]`
- p_boot(gt0): `1.0`

Interpretation: under corrected latency semantics, **router is worse than P5** on the Phase9 strict test set.

### 2.2 Decomposition: route-only gain vs probe overhead
Re-derivation from stored artifacts (Phase9 test, 5 seeds):
- mean route-only ΔJ (P5 − router, **excluding** probe runtime): `-0.000305`
- mean probe overhead term `E[probe_runtime_ms/T_ref]`: `+0.130095`
- mean total ΔJ (including probe runtime): `-0.130400`

Conclusion: the strict degradation is dominated by **probe runtime overhead**; additionally, under α=0.05 the probe stage provides ~zero route-only benefit vs P5.

### 2.3 Phase13 (SOTA fairness) and Phase22 (direct baselines)
Strict reruns also become negative:
- Phase13: mean J-improve vs strongest baseline = `-0.841%`  
  (`outputs/router_phase13_sota_v5_strict_alpha05_probeT_noleak/stats.json`)
- Phase22: mean J-improve vs best direct baseline = `-0.852%`  
  (`outputs/router_phase22_direct_baselines_v5_strict_alpha05_probeT_noleak/stats.json`)

---

## 3. Conclusion (Validity + Claim status)

1) The remaining V1 threats are resolved:
   - α aligns with the frozen protocol,
   - probe runtime is included in `J`,
   - no oracle per-sample cost feature is used,
   - dataset-ID memorization features are removed,
   - the strict bundle is hash-consistent.

2) After these fixes, the strict evidence indicates:
   - **P6 does not beat P5** (Phase9 pooled ΔJ is significantly negative),
   - downstream “SOTA/fairness/direct baseline” advantages also do not hold under this strict semantics.

Therefore, any paper-level “strict improvement” claims must be **reframed** to match `reports/router_strict_audit_v2.md` / `outputs/final_v5_strict/manifest.json`.

