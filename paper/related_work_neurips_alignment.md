# Related-Work Alignment (NeurIPS/ICML framing) — Phase22 Direct Baselines

This note is a **paper-facing** alignment aid: it states how our method maps to close NeurIPS/ICML-adjacent prior work, and documents the *direct baseline implementations* used to prevent “this is just CDT/CRC applied” rejections.

Protocol references:
- frozen protocol source of truth: `docs/router_protocol_v1.md`
- current-mainline companion note: `docs/router_protocol_v1_current_mainline_note.md`
- frozen paper-facing claim contract: `paper/router_current_mainline_claim_contract.md`

Interpretation note:
- this file mainly records the **historical dual-path/direct-baseline alignment** under Protocol V1;
- the **current strict-positive mainline** has already switched to the zero-probe weighted-search line, so any paper-facing reading of this note should be paired with `paper/router_current_mainline_claim_contract.md`.

## 1. Mapping: what part of our router corresponds to what literature?

Historical note: the old dual-path line viewed routing as **risk-bounded adaptive computation** over `fast/slow`: choose a low-latency action (`fast`) or a higher-quality reference action (`slow`) under a frozen risk event (see `docs/router_protocol_v1.md`). The current mainline should instead be read through `paper/router_current_mainline_claim_contract.md` as **single-search compute shaping** over weighted-search arms.

### Conformal decision / risk control (CDT / CRC)
Our **static** routing stage (“use `fast` unless risk-per-compute is too high”) is conceptually aligned with:
- **Conformal decision-making** (cost-aware decision under calibrated uncertainty), and
- **Conformal risk control / selective decision** (choosing a subset of accepted decisions under a risk budget).

In our implementation, this corresponds to:
- learning a risk proxy (probability of violating `q_rel > epsilon_rel` under `fast`),
- conformalizing it to an upper estimate (`p_upper`),
- ranking queries by a risk (or risk-per-compute) score and selecting which ones to escalate.

### Meta-reasoning / adaptive compute (“when to compute more”)
Our **probe** stage (a short, cheap computation to extract early planning signals and decide whether to “continue computing”) corresponds to meta-reasoning / budgeted decision making.

Crucially, our probe is **monotone-safe** by construction: it only flips `fast -> slow`, so the violation probability cannot increase.

## 2. Phase22 “direct baselines” (implemented under the frozen protocol)

Phase22 implements direct CDT/CRC-style baselines on the **same counterfactual tables** and with the same compute accounting convention (probe time counted when used).

Run:
```bash
python scripts/run_router_phase22_direct_baselines.py --enforce-gate
```

### Baseline A (CRC-style): `crc_static_pupper_v1`
**Idea:** learn a violation probability and apply a conformal upper bound `p_upper`; under a fixed escalation budget, flip the highest-risk `fast` queries to `slow`.

Implementation sketch (see `scripts/run_router_phase22_direct_baselines.py`):
1. Fit a violation classifier on calibration `P(q_rel > epsilon_rel | static_features)`.
2. Split-conformalize into `p_upper = clip(p_hat + q_difficulty, 0, 1)`.
3. Under the “start from P5 and flip a fixed number of P5-fast cases per difficulty” convention, flip the top-risk cases to slow.

### Baseline B (CDT-style): `cdt_worstcase_j_v1`
**Idea:** learn a conformal **upper bound** on the positive quality loss `q_pos=max(q_rel,0)` and choose the action that minimizes *worst-case* cost.

Implementation sketch:
1. Fit a regressor for `q_pos`.
2. Split-conformalize to an upper bound `q_pos_upper`.
3. Compute worst-case fast cost `J_fast_upper = T_fast/T_ref + beta*q_pos_upper` and compare to `J_slow = T_slow/T_ref`.
4. Under the same escalation-budget convention, flip cases with the largest `(J_fast_upper - J_slow)` to slow.

## 3. What we learn from Phase22 (and how to write claims honestly)

Artifacts:
- Report: `reports/router_phase22_direct_baselines_v1.md`
- Stats: `outputs/router_phase22_direct_baselines_v1/stats.json`
- Paper table: `paper/tables_router_v7/table_phase22_direct_baselines.csv`

### Key outcome (legacy v1; historical, not strict-audit)
- The best direct baseline is `crc_static_pupper_v1`.
- `crc_static_pupper_v1` is **significantly** better than P5 on `J` under the frozen bootstrap protocol (Phase22 v1 stats/report).
- Our system is best in mean `J`, but the *incremental* improvement over `crc_static_pupper_v1` is small and is **not** significant at `p<0.01` in this run.

### Key outcome (strict calibsplit audit v2; protocol-clean)
Strict audit rerun artifacts:
- Report: `reports/router_phase22_direct_baselines_v2_calibsplit.md`
- Stats: `outputs/router_phase22_direct_baselines_v2_calibsplit/stats.json`
- Paper table: `paper/tables_router_v7_calibsplit_audit/table_phase22_direct_baselines.csv`

What changes under strict audit:
- The best direct baseline becomes `cdt_worstcase_j_v1`.
- Neither (A) ours vs best direct baseline, nor (B) best direct baseline vs P5 achieves `p<0.01` under the frozen bootstrap protocol in this strict rerun.
- In most seeds, ours matches the best direct baseline essentially exactly (see `outputs/router_phase22_direct_baselines_v2_calibsplit/tables/seed_metrics.csv`), i.e. the “incremental method advantage” is **not established** under the strict selection protocol.

### Key outcome (strict full audit v2; deployable semantics)
Strict full-audit artifacts (single source of truth):
- Strict audit report: `reports/router_strict_audit_v2.md`
- Strict bundle (hash-tracked): `outputs/final_v5_strict/manifest.json`
- Phase22 strict artifacts:
  - Report: `reports/router_phase22_direct_baselines_v5_strict_alpha05_probeT_noleak.md`
  - Stats: `outputs/router_phase22_direct_baselines_v5_strict_alpha05_probeT_noleak/stats.json`
  - Paper table: `paper/tables_router_v12_strict_alpha05_probeT_noleak/table_phase22_direct_baselines.csv`

Outcome under strict full audit:
- The best direct baseline is `cdt_worstcase_j_v1`.
- (A) **Ours vs best direct baseline** is **not** a win under strict semantics: mean `J`-improve is negative and the pooled bootstrap does not support `p<0.01`.
- (B) Best direct baseline vs P5 is also **not** significant at `p<0.01` under strict.

Interpretation:
- Under the frozen protocol with deployable semantics (probe runtime counted; no oracle per-sample cost; no dataset-ID features), the “incremental method advantage” over CDT/CRC-style direct baselines is **not established** and the performance-facing claim must be reframed.

### Paper-facing implication
To avoid overclaiming novelty, we should **not** position Algorithm 1 alone as a new ML method beyond CDT/CRC.

Instead, the safe and defensible positioning is:
1. **C2D-RBAC pipeline contribution:** a counterfactual-to-deployment framework with a frozen protocol, deterministic manifests, and claim-to-evidence audit.
2. **Two-stage monotone-safe probing contribution:** a meta-reasoning escalation stage that is provably non-increasing in violation probability (fast→slow only) with potential `J` gains that must be validated under the strict protocol.
3. **Deployment alignment contribution:** a single hash-tracked policy artifact (`artifacts/router_policy_v1/`) validated against closed-loop runners (Phase17), which is typically missing in CDT/CRC-style offline studies.

Strict-audit update to the claim style:
- Under the strict protocol, point (2) must be stated precisely: the monotone-safe probe guarantees non-increasing risk, but improving `J` is an empirical question that must be validated under strict selection/search.
- Under strict full audit v2 (`reports/router_strict_audit_v2.md`), the empirical evidence currently indicates **no `J` gain** (and slight degradation) for the probe router; the paper should therefore treat probe as a *risk-safe escalation mechanism* whose net `J` benefit depends on amortizing/cheapening probe or increasing route-only gains.

This alignment note therefore reduces novelty risk in two ways:
1) we explicitly implement CDT/CRC-style baselines under the frozen protocol, and  
2) we record both historical (legacy) and protocol-clean (strict) outcomes, so the paper can make defensible claims even when strict evidence forces a performance claim reframe.
