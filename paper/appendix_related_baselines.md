# Appendix: Related-Work Baselines (Phase16)

This appendix documents the *implementation details* and *fairness/budget* assumptions for the Phase16 baselines.

## Protocol and fairness
- All methods are evaluated on the same Phase9 counterfactual tables: `router_counterfactual_{calib,test}.parquet`.
- Objective and risk use the frozen protocol (`docs/router_protocol_v1.md`): `J` and `V=P(delta_l_rel>epsilon_rel)`.
- Baseline models (feature→score) are fit using `calib` only.
- Compute/budget accounting follows the in-repo strict-router convention: all related baselines start from the Phase-5 conformal route and are only allowed to **flip a fixed number of P5-fast cases to slow** (per difficulty).

## Baseline families

### Family A — Rational multi-heuristic deployment (`rational_static_v1`)
**Idea:** a rational escalation rule: “spend extra compute only where it helps most”, using static heuristics.

**Implementation:**
- Start from Phase-5 conformal route (`conformal_strict_v2`).
- Compute a z-scored static heuristic sum on `calib` P5-fast cases (complexity/occupancy/LOS proxies).
- On `test`, among P5-fast cases, flip the top-`k_slow_by_difficulty[d]` cases (largest score) to slow for each difficulty `d`.

### Family B — Conformalized switching / decision (`conformal_switch_static_v1`)
**Idea:** conformalized risk-aware escalation: flip cases that are most likely to incur large quality loss under fast.

**Implementation:**
- Start from Phase-5 conformal route (`conformal_strict_v2`).
- Fit ridge regression on `calib` P5-fast cases to predict `q_rel` from static features.
- Use split conformal residual quantiles to form an upper bound `q_rel_upper`.
- On `test`, among P5-fast cases, flip the top-`k_slow_by_difficulty[d]` cases (largest `q_rel_upper`) to slow for each difficulty `d`.

### Family C — Meta-reasoning / when-to-quit (`meta_quit_probe_v1`)
**Idea:** after a small probe computation, decide whether to “quit early” (stay fast) or “continue computing” (escalate to slow).

**Implementation:**
- Start from Phase-5 conformal route (`conformal_strict_v2`).
- Compute a z-scored probe heuristic sum on `calib` P5-fast cases (success/stagnation/dead-end proxies).
- On `test`, among P5-fast cases, flip the top-`k_slow_by_difficulty[d]` cases (largest score) to slow for each difficulty `d`.

