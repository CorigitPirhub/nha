# Router Protocol V1 (Frozen)

Status: `frozen`  
Version: `v1.0`  
Freeze date: `2026-03-02`

## 1. Scope
This protocol defines the mandatory evaluation and acceptance criteria for the dual-path router (Fast/Slow) in top-tier publication mode.

## 2. Fixed Metrics
1. Primary objective: `J = T_norm + beta * L_norm`
2. Relative quality loss: `delta_l_rel = (L_router - L_slow_ref) / max(L_slow_ref, 1e-6)`
3. Risk budget: `epsilon_rel = 0.015` (1.5%)
4. Violation probability: `V = P(delta_l_rel > epsilon_rel)`
5. Violation target: `alpha = 0.05`
6. Oracle gap: `OG = (J_router - J_oracle) / abs(J_oracle)`

Where:
- `T` is latency in milliseconds.
- `L` is search-quality proxy (default: node expansions; fallback: path-cost increase when expansions unavailable).
- `slow_ref` is the frozen high-quality baseline (`manual_v11b` line).

## 3. Statistical Protocol
1. Seeds: at least `5` random seeds for final reporting.
2. Significance tests:
- Paired bootstrap with `N = 10000`.
- Wilcoxon signed-rank test (paired).
3. Mandatory report fields per main metric:
- `mean`, `std`, `95% CI`, `p-value`.
4. Main claims are valid only if:
- `p < 0.01`, and
- `95% CI` does not cross zero for improvement direction.

## 4. Dataset Protocol
The mixed-difficulty benchmark (`router_mixed_v1`) must satisfy:
1. Test size `>= 900`.
2. Each difficulty bucket (`easy`, `medium`, `hard`) has `>= 250` test cases.
3. OOD map-family proportion in test set `>= 30%`.
4. Split manifests are deterministic under fixed seed and hash-stable.

## 5. Phase Gate Targets (P0-P2)
1. P0 gate:
- This protocol file exists and is frozen with explicit values:
  `epsilon_rel=1.5%`, `alpha=0.05`, bootstrap `N=10000`.
2. P1 gate:
- Mixed dataset created with required counts and OOD ratio.
3. P2 gate:
- Counterfactual labeling coverage `100%`.
- Missing required fields `0`.
- Coefficient of variation (CV) for key repeated-sampling statistics `<= 5%`.

## 6. Reporting Artifacts
Required artifacts:
1. `data/router_mixed_v1/manifest.json`
2. `outputs/router_counterfactual_v1.parquet`
3. `outputs/router_counterfactual_v1_report.json`

## 7. Change Control
Any protocol change after freeze requires:
1. New version tag.
2. Explicit rationale in changelog.
3. Re-running all affected phase validations.
