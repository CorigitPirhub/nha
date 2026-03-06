# Router Validity Audit (V1)

Date: 2026-03-05  
Scope: **Dual-Path Router** mainline — assess whether the *reported* strict advantages (Phase9/13/22) are attributable to the method/design rather than: implementation bugs, dataset leakage, cherry-picking, fabricated numbers, or inconsistent evaluation semantics.

> ⚠️ **Deprecated (superseded by v2):** This V1 audit identified several major threats to validity (α mismatch, probe runtime not counted in \(J\), oracle cost feature leakage).
> After fixing them, the strict mainline conclusion flips and the performance-facing claim no longer holds; see `reports/router_validity_audit_v2.md` and `reports/router_strict_audit_v2.md`.

This audit is **artifact-driven**: it re-derives key metrics directly from stored parquet/JSON artifacts, checks split integrity, and checks strict selection/search provenance.

---

## 0. Executive Summary

### High-confidence OK
- **No split overlap**: `router_phase9_public_v1` and `router_mixed_v1` have **0 overlap** by `source_path` across `train/calib/test`.
- **Strict selection is actually strict** (no test tuning):
  - Phase8 selection/search uses `calib_train/calib_val` only (`selection_split=calib`), and `test` is used for one-time final evaluation.
- **Reported numbers are not “hand-written”**:
  - Phase9/13/22 `stats.json` values are **exactly reproducible** from stored decision parquets + counterfactual tables.
- **Counterfactual tables are consistent with code**:
  - Spot-check recomputation of `L_fast/L_slow` for sampled cases matches stored parquets exactly.
- **Parquet overwrite / cache hazards are mitigated** in the strict mainline:
  - Key phases write `inputs_parquet_sha256.json`, and Phase9 detects overwritten inputs and forces rerun.

### Major threats to validity (must resolve before “risk-bounded + deployable” top-tier claims)
1) **Risk budget mismatch vs frozen protocol**  
   `docs/router_protocol_v1.md` freezes \(\alpha=0.05\), but the strict Phase9 instantiation uses `strict_violation_target=0.20` and yields test violation rates ~**0.18–0.19** (18–19%). This is not consistent with \(\alpha=0.05\).

2) **Probe compute is not counted in the primary objective \(J\)**  
   Phase9/13/22 compute \(J\) using `T_fast_ms/T_slow_ms` only; probe runtime (`probe_runtime_ms`) is tracked but **not included** in \(T\) inside \(J\). If probe is treated as extra latency and added for the probe policy, the Phase9 P5→P6 gain can reverse sign.

3) **Oracle feature leakage into routing (deployment misalignment risk)**  
   The strict Phase9 probe uses `probe_include_cost_feature=True`, injecting `c = T_slow_ms - T_fast_ms` (counterfactual-derived) into the gain predictor. Per-query `c` is not available before committing to slow; it must be predicted from deployable features or the evaluation must be explicitly framed as oracle-cost.

### Minor integrity drift
- `outputs/final_v4_strict/manifest.json` hashes match for the main `stats.json` files, but the recorded hash for `docs/neurips_method_v1.md` does **not** match the current on-disk file (snapshot drift).

---

## 1. What Was Checked (with artifact pointers)

### 1.1 Split integrity (no overlap)
Checked overlap by exact `source_path`:
- `data/router_phase9_public_v1/{train,calib,test}_index.csv` → overlap = 0 across all pairs.
- `data/router_mixed_v1/{train,calib,test}_index.csv` → overlap = 0 across all pairs.

### 1.2 Counterfactual table coverage / provenance
For strict Phase9 (`outputs/router_phase9_bench_v6_strict_knapsack`):
- `common/router_counterfactual_calib.parquet` matches `data/router_phase9_public_v1/calib_index.csv` exactly by `sample_name` (1800 rows).
- `common/router_counterfactual_test.parquet` matches `data/router_phase9_public_v1/test_index.csv` exactly by `sample_name` (3218 rows).
- Counterfactual report explicitly records `device="cpu"` and Phase2 CV gate pass:
  - `outputs/router_phase9_bench_v6_strict_knapsack/common/router_counterfactual_test_report.json`

### 1.3 Counterfactual correctness (spot-check recomputation)
For sampled cases across difficulty buckets, recomputing A* expansions matches stored values exactly:
- fast expansions from `scripts/evaluate_baselines.py:_astar_grid(..., heuristic_map=None)`
- slow expansions from `network/inference.py:NeuralHeuristicPredictor.predict_field` → `_resolve_2d_heuristic` → `_astar_grid(..., heuristic_map=h_slow)`

### 1.4 Strict selection/search provenance (no test tuning)
Strict Phase9 configuration is recorded in:
- `outputs/router_phase9_bench_v6_strict_knapsack/stats.json` → `router_eval_config`:
  - `calib_split_mode=train_val`
  - `conformal_select_on=calib`
  - `probe_search_on=calib`
  - `phase8_probe_selection_mode=knapsack_lcb`

Per-seed Phase8 policy artifacts confirm:
- `outputs/router_phase9_bench_v6_strict_knapsack/router_eval/seeds/seed_*/mixed/*/policy_metrics.json`
  - `selected_policy.selection_split = "calib"`

### 1.5 Reported Phase9/13/22 metrics are exactly reproducible from artifacts
Re-derivation (from stored parquets) matches the shipped `stats.json` bit-for-bit:
- Phase9: `outputs/router_phase9_bench_v6_strict_knapsack/stats.json`
- Phase13: `outputs/router_phase13_sota_v4_strict_knapsack/stats.json`
- Phase22: `outputs/router_phase22_direct_baselines_v4_strict_knapsack/stats.json`

The strict “single source of truth” summary is:
- `reports/router_strict_audit_v1.md`

### 1.6 SHA256 binding / cache guard coverage
Presence of `inputs_parquet_sha256.json`:
- `outputs/router_phase9_bench_v6_strict_knapsack/common/risk/inputs_parquet_sha256.json`
- `outputs/router_phase9_bench_v6_strict_knapsack/router_eval/inputs_parquet_sha256.json`
- `outputs/router_phase13_sota_v4_strict_knapsack/inputs_parquet_sha256.json`
- `outputs/router_phase22_direct_baselines_v4_strict_knapsack/inputs_parquet_sha256.json`

Overwrite detection exists in Phase9 runner:
- `scripts/run_router_phase9_bench.py:main` uses `utils/parquet_guard.py:compare_record`.

### 1.7 Bundle hash drift check
`outputs/final_v4_strict/manifest.json`:
- hashes match for the strict `stats.json` files and `docs/router_protocol_v1.md`;
- hash mismatch for `docs/neurips_method_v1.md` indicates the repo changed after snapshot creation.

---

## 2. Findings: Is the advantage “really from the method”?

### 2.1 Not from train/test split leakage (strict chain is consistent)
Evidence:
- strict selection/search is `calib_train/calib_val` only (recorded in `router_eval_config` and policy artifacts).
- strict results remain significantly positive in Phase9/13/22 (see `reports/router_strict_audit_v1.md`).

### 2.2 Not from fabricated / inconsistent statistics
Evidence:
- Phase9/13/22 summary numbers are exactly reproducible from stored parquets.
- Counterfactual tables pass coverage and CV gates (`router_counterfactual_*_report.json`).
- Spot-check recomputation matches stored expansions exactly (rules out “hand-written parquet” for the checked samples).

### 2.3 The advantage is **highly sensitive** to latency semantics (probe cost)
Stored artifacts show:
- mean probe runtime on Phase9 test: ~0.89 ms (`router_eval/common/probe_features_test.parquet`)
- mean fast runtime: ~0.77 ms (`common/router_counterfactual_test.parquet`)
- slow runtime is dominated by neural inference (`infer_slow_ms` mean ~129.8 ms; median ~8.0 ms)

Current \(J\) used in Phase9/13/22 ignores probe runtime.
If probe runtime is treated as *extra* latency and added to the probe policy only, the Phase9 pooled ΔJ (P5 − probe) can become negative.

Interpretation:
- This is **not** a code bug in the metric computation; it is a **semantic choice** about what “latency \(T\)” includes.
- For paper validity, you must either:
  - (A) implement probe extraction as amortized work inside the fast run (so it is not extra), and demonstrate this alignment, or
  - (B) include probe runtime in \(T\) for policies that use probe and rerun strict results.

### 2.4 The “risk-bounded” framing is currently inconsistent with the strict Phase9 instantiation
Frozen protocol:
- `docs/router_protocol_v1.md` declares \(\alpha=0.05\).

Strict Phase9 instantiation:
- `outputs/router_phase9_bench_v6_strict_knapsack/stats.json` records:
  - `phase8_strict_violation_target = 0.20`
  - `phase8_strict_ci_upper_target = 0.22`
- The resulting test violation rates for P5 are ~0.18–0.19 (per seed).

Additionally, Phase8 strict report keys are misleading:
- `scripts/run_router_phase8_strict.py` uses gate keys named `strict_violation_rate_le_8pct` / `strict_violation_ci95_upper_le_9pct`,
  but actually checks against `args.strict_violation_target` / `args.strict_ci_upper_target` (which Phase9 sets to 0.20/0.22).

Interpretation:
- Current strict Phase9/13/22 results are valid **under the actual risk targets used**, but they do **not** support a claim of \(\alpha=0.05\) compliance.

### 2.5 Deployment alignment risk: oracle `c` as a feature
Strict Phase9 uses `phase8_probe_include_cost_feature=true`, so the probe gain predictor sees:
- `c = T_slow_ms - T_fast_ms` (counterfactual-derived per sample).

This value is not available before selecting slow in real deployment; it must be replaced by a predicted \(\hat c(x)\) (from deployable features), or the evaluation must clearly state it is oracle-cost.

### 2.6 “Dataset luck” check (weak but suggestive)
Within the strict Phase9 artifacts:
- P5→probe ΔJ is positive across 5 seeds and across `mp` and `csm` benchmark sources (direction-consistent in `stats.json`).
- By difficulty, ΔJ is positive for `easy/medium/hard` (medium smaller but still positive).

This reduces (but does not eliminate) the likelihood that gains are from a single tiny slice.

---

## 3. Recommended Next Actions (to close remaining validity gaps)

1) **Protocol alignment**
- Either rerun strict Phase9/13/22 with \(\alpha=0.05\) (and consistent CI targets), or version the protocol (`router_protocol_v2.md`) and update all main-table claims accordingly.

2) **Latency semantics**
- Decide and document whether probe compute is included in \(T\).
- If included: update \(J\) computation in Phase8/9/13/22 and rerun strict chain.
- If amortized: implement probe feature extraction as instrumentation of the fast run and provide an alignment check (offline policy == deployment behavior).

3) **Remove oracle features for deployable claims**
- Replace `c` with a learned/predicted \(\hat c(x)\) from deployable features, then rerun strict chain to ensure conclusions hold.

4) **Fix misleading gate labels**
- Rename Phase8 strict gate keys to reflect the actual numeric thresholds (avoid “8%/9%” hard-coded naming).

5) **Generalization beyond ID memorization**
- Add an ablation that removes `map_id/scenario/source_dataset` categorical features (or hold out map-id families) and report the delta in Phase9/13/22.
