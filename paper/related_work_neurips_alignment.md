# Related-Work Alignment (NeurIPS/ICML framing) — Phase22 Direct Baselines

This note is a **paper-facing** alignment aid: it states how our method maps to close NeurIPS/ICML-adjacent prior work, and documents the *direct baseline implementations* used to prevent “this is just CDT/CRC applied” rejections.

## 1. Mapping: what part of our router corresponds to what literature?

We view dual-path routing as **risk-bounded adaptive computation**: choose a low-latency action (`fast`) or a higher-quality reference action (`slow`) under a frozen risk event (see `docs/router_protocol_v1.md`).

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

### Key outcome (strict recovery v6; protocol-clean + main-claim-valid)
This project now includes a strict, protocol-clean recovery that restores significance without any test-set tuning:
- Strict audit report (single source of truth): `reports/router_strict_audit_v1.md`
- Phase22 strict (recovery) artifacts:
  - Report: `reports/router_phase22_direct_baselines_v4_strict_knapsack.md`
  - Stats: `outputs/router_phase22_direct_baselines_v4_strict_knapsack/stats.json`
  - Paper table: `paper/tables_router_v11_strict_knapsack/table_phase22_direct_baselines.csv`

Outcome under strict recovery:
- The best direct baseline remains `cdt_worstcase_j_v1`.
- (A) **Ours vs best direct baseline** is a significant win under the frozen bootstrap protocol (`p<0.01`, CI not crossing 0).
- (B) Best direct baseline vs P5 is also significant in this recovered strict rerun.

### Paper-facing implication
To avoid overclaiming novelty, we should **not** position Algorithm 1 alone as a new ML method beyond CDT/CRC.

Instead, the safe and defensible positioning is:
1. **C2D-RBAC pipeline contribution:** a counterfactual-to-deployment framework with a frozen protocol, deterministic manifests, and claim-to-evidence audit.
2. **Two-stage monotone-safe probing contribution:** a meta-reasoning escalation stage that is provably non-increasing in violation probability (fast→slow only) with potential `J` gains that must be validated under the strict protocol.
3. **Deployment alignment contribution:** a single hash-tracked policy artifact (`artifacts/router_policy_v1/`) validated against closed-loop runners (Phase17), which is typically missing in CDT/CRC-style offline studies.

Strict-audit update to the claim style:
- Under the strict protocol, point (2) must be stated precisely: the monotone-safe probe guarantees non-increasing risk, but improving `J` is an empirical question that must be validated under strict selection/search.
- With Phase27 strict recovery (`reports/router_strict_audit_v1.md`), the incremental `J` gain (including vs direct CDT/CRC baselines) is now supported under strict audit; the paper can therefore keep a performance-facing main claim, but should still retain the strict-v2 failure mode as an explicit limitation / ablation narrative.

This alignment note therefore reduces novelty risk in two ways:
1) we explicitly implement CDT/CRC-style baselines under the frozen protocol, and  
2) we record both historical (legacy) and protocol-clean (strict) outcomes, so the paper can make defensible claims regardless of whether strict recovery succeeds.
