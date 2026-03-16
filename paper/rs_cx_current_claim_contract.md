# RS/CX Current Claim Contract

Status: `frozen-paper-facing-contract`
Date: `2026-03-08`

This file defines the **current paper-facing claim boundary** for the
`RS cost field + CX3-D / RS-HPG` branch.

It exists to prevent future writing from accidentally overstating the current evidence.

## 1. Method object

Current accepted branch:
- `RS cost field` as the analytical base heuristic
- plus `CX3-D / RS-HPG` as a **topology-preserving guarded structural edit**
- with the accepted narrow refinement `low_bridge_scale`

Accepted evidence roots:
- `docs/rs_field_root_protocol_v1.md`
- `reports/rs_p0cx3_round1_summary.md`
- `reports/rs_p0cx3_stats_v1.md`
- `reports/rs_p0cx3_cx3_d_aux_followup_v1.md` (negative follow-up evidence)
- `reports/rs_p0cx3_cx3_d_recovery_followup_v1.md` (negative dev-only follow-up evidence)
- `TASK.md`

## 2. What may be claimed

The strongest currently honest claim is:

- Under the frozen public `parasol_narrow` protocol and same-`alpha` comparison against `Plain-Residual`,
  `RS + CX3-D / RS-HPG` provides a **small but stable protected efficiency gain**, especially by
  avoiding the `parasol_misc` regression that broke earlier structural-edit branches.

Equivalent allowed wording:
- `RS-HPG` turns structural heuristic editing into a **protected conservative refinement** of the current `RS`-grounded baseline.
- The current value of `CX3-D` is **not** success lifting, but **protected search-effort reduction without harming misc success**.
- The most reliable current gain appears on the protected `parasol_misc` subgroup, while overall mean gains remain modest.

## 3. What may not be claimed

The following claims are currently **not allowed**:

- that `CX3-D` restores the public success axis to `1.0`
- that `CX3-D` is already SOTA on the nearest fair baseline comparison
- that `CX3-D` establishes a decisive overall advantage interval on the public 18-case bundle
- that `CX3-D` dominates `Plain-Residual` or `Full` on every subgroup
- that expanded `rs_root_hard_v2/test` evidence supports the current branch (it does not; expanded-hard follow-ups are not accepted evidence)
- that `CX3-C` is still the main positive branch (it is not after the corrected reruns)

## 4. Nearest baselines by claim level

For the **root RS-field claim**:
- nearest baseline remains `Hybrid A* (RS)` under `docs/rs_field_root_protocol_v1.md`

For the **current CX3-D module claim**:
- nearest baseline is `Plain-Residual (same α)`
- frozen auxiliary references remain:
  - `Full`
  - `No-Residual`
  - `A*` on `mp/csm`

## 5. Current evidence interpretation

What the evidence currently supports:
- `CX3-D` keeps public success unchanged relative to same-`alpha` `Plain-Residual`
- `CX3-D` protects `parasol_misc` and improves its search effort
- `CX3-D` yields a small positive average search-effort delta on the public bundle
- `CX3-D` keeps ordinary-scene expansions close to `A* / Full`, though time overhead still exists

What the evidence currently does not support:
- statistically hard overall improvement at the full-bundle level
- broad hard-family amplification (`narrow_passage` still remains a weak point)
- a paper main claim built around strong average superiority

## 6. Paper-facing one-sentence template

Current safe template:

- `On the frozen public parasol benchmark, adding the topology-preserving guard RS-HPG to the RS-grounded heuristic yields a small protected efficiency gain over the same-alpha residual baseline, chiefly by eliminating the parasol_misc regression that affected earlier structural-edit variants.`

## 7. Current paper positioning

The correct current positioning is:
- `RS cost field` remains the **root analytical innovation**
- `CX3-D / RS-HPG` is the **current best conservative refinement branch**
- this branch is best viewed as a **robustness / protection mechanism**, not yet as the final winning high-gain method

In other words:
- it is valid to position `CX3-D` as the current main accepted refinement inside the RS-grounded line;
- it is not yet valid to position it as the final completed answer to `P0-CX`.
