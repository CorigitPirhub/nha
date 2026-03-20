# RS/CX Current Claim Contract

Status: `frozen-paper-facing-contract`
Date: `2026-03-17`

This file defines the **current paper-facing claim boundary** for the
`RS cost field + CX34-A / Subtype-Specific Macro Rescue` branch.

It exists to prevent future writing from accidentally overstating the current evidence.

Candidate note:
- the leading **fusion-mainline candidate** is now tracked separately in
  `paper/rs_cx_fusion_candidate_contract.md`
- that candidate currently corresponds to
  `RS + CX34-A + CX42-B / Query Compatibility Release`
- it is **not** yet the frozen paper-facing accepted branch

## 1. Method object

Current accepted branch:
- `RS cost field` as the analytical base heuristic
- plus `CX34-A / Subtype-Specific Macro Rescue` as a **misc-subtype-specific action-language extension**
- implemented as an extra custom reverse macro `(9, 9)` scoped to the low-bridge / mid-focus / high-openness misc subtype

Accepted evidence roots:
- `docs/rs_field_root_protocol_v1.md`
- `reports/rs_p0cx34_round1_summary.md`
- `reports/rs_p0cx34_a_pilot_v1.md`
- `reports/rs_p0cx34_standard_audit_v1.md`
- `reports/rs_p0cx34_recheck_audit_v1.md`
- `reports/rs_p0cx34_a_hard_eval_v1.md`
- `TASK.md`

Canonical artifact note:
- the accepted public/full-support numbers are frozen to `outputs/rs_p0cx34_a_pilot_v1`
- the accepted hard-test numbers are frozen to `outputs/rs_p0cx34_a_hard_eval_cuda_v1`
- `reports/rs_p0cx34_recheck_audit_v1.md` shows that the qualitative public conclusion is stable under CPU/GPU reruns, but exact metrics are mildly device-sensitive

## 2. What may be claimed

The strongest currently honest claim is:

- Under the frozen public `parasol_narrow` protocol and the frozen `rs_root_hard_v2/test` evaluation,
  `RS + CX34-A / Subtype-Specific Macro Rescue` is the strongest RS-grounded branch so far:
  it removes the public `parasol_misc` deficit on the canonical public artifact and transfers positively overall on hard-test
  relative to `CX3-D` (`success_delta_pp = +2.740`, `exp_delta = +196.548` on the frozen hard-test artifact).

Equivalent allowed wording:
- `CX34-A` is the first RS-grounded branch that makes public `parasol_misc` non-negative without reopening the `maze` deficit.
- The key mechanism is not another gate or threshold repair, but a **subtype-specific macro language object** that directly repairs the remaining misc subtype.
- The current value of `CX34-A` is **public family-deficit elimination plus positive hard-test transfer**, not deployable runtime or family-uniform dominance.

## 3. What may not be claimed

The following claims are currently **not allowed**:

- that `CX34-A` is already a deployable low-overhead solution
- that the exact public metrics are device-invariant across CPU and GPU inference
- that the exact hard-test metrics are device-invariant across CPU and GPU inference
- that `CX34-A` is the final completed answer to `P0-CX`
- that `CX34-A` dominates every family or every future hard-family benchmark
- that `CX34-A` is path-quality clean on hard-test

## 4. Nearest baselines by claim level

For the **root RS-field claim**:
- nearest baseline remains `Hybrid A* (RS)` under `docs/rs_field_root_protocol_v1.md`

For the **current CX34-A module claim**:
- nearest parent baseline is `CX33-B / Budgeted Stubborn-Slice Repair`
- long-horizon accepted predecessor remains `CX3-D / RS-HPG`
- frozen auxiliary references remain:
  - `Plain-Residual`
  - `Full`
  - `A*` on `mp/csm`

## 5. Current evidence interpretation

What the evidence currently supports:
- on the canonical artifact, `CX34-A` lifts public `exp_delta` to `+420.389`
- on the canonical artifact, `CX34-A` moves public `parasol_misc` from `-16.333` to `+10.500`
- on the canonical artifact, `CX34-A` keeps `maze = 0.0`, `flange = +1421.0`, and `narrow_passage = +99.75`
- the `mp/csm` ordinary-support audit remains exact (`max_abs_field_diff = 0.0`)
- the cross-device recheck preserves the same qualitative conclusion even though exact numbers move
- on the frozen hard-test artifact, `CX34-A` improves over `CX3-D` by `success_delta_pp = +2.740` and `exp_delta = +196.548`

What the evidence currently does not support:
- low-overhead deployment
- a device-free exact-number claim without freezing the evaluation device / artifact
- family-uniform hard-test gains (`deadend_labyrinth`, `flange`, and `parasol_misc` still regress on hard-test)
- path-quality-clean hard-test gains (`path_delta = -1.179` overall, with a large negative `alpha_puzzle` slice)
- a paper main claim built around final across-distribution closure

## 6. Paper-facing one-sentence template

Current safe template:

- `On the frozen public parasol benchmark and frozen rs_root_hard_v2 hard benchmark, the RS-grounded CX34-A subtype-specific macro rescue removes the public parasol_misc deficit and improves overall hard-test success and search effort over CX3-D, though runtime overhead and several hard-family/path-quality caveats remain.`

## 7. Current paper positioning

The correct current positioning is:
- `RS cost field` remains the **root analytical innovation**
- `CX34-A / Subtype-Specific Macro Rescue` is the **current accepted RS-grounded refinement branch with positive public and hard-test evidence**
- this branch is best viewed as a **mechanism-level breakthrough on the misc deficit plus positive hard-test transfer**, not yet as the final deployable method
- the leading fusion/runtime candidate is tracked separately as `CX42-B`, but after the unified public rerun that branch should be read as a hard-runtime candidate rather than a confirmed public upgrade, and it has not replaced the frozen accepted claim branch

In other words:
- it is valid to position `CX34-A` as the current main accepted refinement inside the RS-grounded line
- it is not yet valid to position it as the final completed answer to `P0-CX`
