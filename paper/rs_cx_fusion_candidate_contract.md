# RS/CX Fusion Candidate Contract

Status: `candidate-contract`
Date: `2026-03-19`

This file defines the **current fusion-mainline candidate boundary** for the
`RS + CX34-A + CX42-B / Query Compatibility Release` branch.

It exists to keep the candidate line clearly separated from the
still-frozen paper-facing accepted branch `RS + CX34-A / Subtype-Specific Macro Rescue`.

## 1. Candidate method object

Current fusion candidate:
- `RS cost field` as the analytical base heuristic
- `CX34-A / Subtype-Specific Macro Rescue` as the accepted misc-subtype-specific action-language object
- `CX41-B / Frontier-Dominance Review Gate` as the validated lightweight runtime-reduction mechanism
- `CX42-B / Query Compatibility Release` as a **query-level selective release layer** that decides when to keep `CX34-A` and when to switch to the lighter `CX41-B`-style branch

In plain terms:
- `CX34-A` remains the default branch
- `CX41-B` is treated as a compatibility branch, not as a replacement branch
- `CX42-B` learns when `CX41-B` is safe enough to release without degrading the `CX34-A` effect profile

Evidence roots:
- `reports/rs_p0cx42_b_pilot_v1.md`
- `reports/rs_p0cx42_public_compare_v1.md`
- `reports/rs_p0cx42_b_hard_eval_v1.md`
- `reports/rs_p0cx41_b_pilot_v1.md`
- `reports/rs_p0cx41_b_hard_eval_v1.md`
- `reports/rs_p0cx34_a_pilot_v1.md`
- `reports/rs_p0cx34_a_hard_eval_v1.md`
- `TASK.md`

## 2. What may currently be claimed

The strongest currently honest candidate-level claim is:

- On the frozen `rs_root_hard_v2/test` hard benchmark,
  `CX42-B / Query Compatibility Release` preserves the frozen `CX34-A`
  `success / expansions / path` profile while reducing runtime.
- On the unified public rerun `reports/rs_p0cx42_public_compare_v1.md`,
  `CX42-B` does **not** currently show a confirmed advantage over `CX34-A`:
  `success_delta_pp = 0.000`, `exp_delta = 0.000`,
  and `mean_time_overhead_ratio = +0.010346`.

Equivalent allowed wording:
- `CX42-B` is the first branch that turns `CX41-B` from a competing continuation line into a lightweight compatibility layer for `CX34-A`.
- The key mechanism is not node-level pruning inside `CX34-A`, but a **query-level compatibility release contract**.
- The current value of `CX42-B` is **candidate-level fusion of accepted effect profile plus hard-test runtime reduction**, not yet full paper-facing replacement.

## 3. What may not be claimed

The following claims are currently **not allowed**:

- that `CX42-B` is already the paper-facing accepted mainline
- that `CX42-B` dominates `CX34-A` on every metric and every benchmark
- that `CX42-B` has already replaced `CX34-A` in the frozen claim contract
- that `CX42-B` has solved all deployment/runtime issues
- that `CX42-B` is family-uniformly better than `CX34-A`
- that `CX42-B` has a confirmed public improvement over `CX34-A`

## 4. Current evidence interpretation

What the evidence currently supports:
- on the unified public rerun, `CX42-B` is effectively tied with `CX34-A` on public search effect:
  - `success_delta_pp = 0.000`
  - `exp_delta = 0.000`
  - `mean_time_overhead_ratio = +0.010346`
- the unified public ablation shows `CX42-B (Full)` is nearly identical to `CX42-B (Always-CX34)`:
  - `exp_delta = 0.000`
  - `mean_time_overhead_ratio = -0.010013` vs full
- on the frozen hard-test artifact, `CX42-B` preserves `CX34-A` exactly on:
  - success
  - expansions
  - path length
  while improving runtime by:
  - `mean_time_overhead_ratio = -0.289825` vs `CX34-A`
- relative to `CX41-B`, the fusion line keeps the lighter branch's effect profile while reducing runtime on both public and hard-test

What the evidence currently does not support:
- public improvement over `CX34-A`
- paper-facing replacement of `CX34-A`
- exact device-invariant metric claims without freezing the device/artifact
- final across-distribution closure
- a claim that the fusion line is already the completed answer to `P0-CX`

## 5. Recommended current positioning

The correct current positioning is:
- `RS + CX34-A` remains the frozen paper-facing accepted branch
- `CX42-B` is the **leading hard-runtime fusion candidate**
- this candidate is best viewed as a **compatibility release layer with hard-test runtime evidence**, not yet as a fully promoted replacement

## 6. Safe one-sentence template

- `On the frozen rs_root_hard_v2 hard benchmark, the RS-grounded CX42-B query-compatibility-release branch preserves the accepted CX34-A effect profile while reducing runtime, but its public advantage over CX34-A is not confirmed under unified rerun, so it remains a compatibility-layer candidate rather than the frozen accepted claim branch.`
