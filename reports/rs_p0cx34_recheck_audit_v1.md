# P0-CX34 Recheck Audit V1

- date: `2026-03-17`
- scope: validate whether `CX34-A / Subtype-Specific Macro Rescue` is reproducible enough to be merged into the current RS-grounded mainline
- canonical artifact: `outputs/rs_p0cx34_a_pilot_v1`
- canonical summary root: `reports/rs_p0cx34_round1_summary.md`
- canonical support audit: `reports/rs_p0cx34_standard_audit_v1.md`

## Audit Questions

1. Does the stored `CX34-A` conclusion reproduce under the same protocol inputs?
2. If a rerun disagrees, is the cause protocol drift / leakage, or only numerical device sensitivity?
3. Is the conclusion strong enough to promote `CX34-A` into the current RS-grounded mainline?

## Input Integrity

- `inputs_sha256` matches between:
  - `outputs/rs_p0cx34_a_pilot_v1/inputs_sha256.json`
  - `outputs/verify_cx34_recheck_v2/rs_p0cx34_a_pilot_v1/inputs_sha256.json`
- `mp/csm` ordinary-support audit remains exact:
  - `mp`: `max_abs_field_diff = 0.0`
  - `csm`: `max_abs_field_diff = 0.0`
- no new split, benchmark, or hard-test file was introduced during recheck

## Recheck Runs

### 1. Canonical CPU-style public rerun

- artifact: `outputs/verify_cx34_cpu_param078_public_v1`
- protocol: same `calib_hard_v1` inputs, same frozen `CX33-B` parent references, public-only rerun with the canonical `CX34-A` params (`macro_bridge_min = 0.078`)
- outcome vs `CX3-D`:
  - `exp_delta = +420.500`
  - `parasol_misc = +10.833`
  - `maze = 0.0`
  - `flange = +1421.0`
  - `narrow_passage = +99.75`
- comparison to canonical stored artifact:
  - `exp_delta`: `+420.389 -> +420.500` (`+0.111`)
  - `parasol_misc`: `+10.500 -> +10.833` (`+0.333`)
  - `maze / flange / narrow_passage`: exact match

Interpretation:
- the stored `CX34-A` public conclusion is reproducible on a CPU-style rerun to within negligible numerical drift

### 2. GPU shadow rerun

- artifact: `outputs/verify_cx34_recheck_v2/rs_p0cx34_a_pilot_v1`
- protocol: full rerun with `--device cuda`, including public eval and ordinary-support audit
- outcome vs `CX3-D`:
  - `exp_delta = +422.722`
  - `parasol_misc = +12.333`
  - `maze = 0.0`
  - `flange = +1428.4`
  - `narrow_passage = +98.25`
- ablation remains directional:
  - `No-Custom-Macro-Rescue`: `exp_delta = +412.722`, `parasol_misc = -17.667`

Interpretation:
- exact public numbers shift under GPU inference, but the qualitative result is unchanged and in fact stronger overall
- the custom macro rescue remains the decisive mechanism-level object

## Root-Cause Reading of the Mismatch

- the mismatch is **not** explained by:
  - split drift
  - benchmark drift
  - support-audit failure
  - a changed frozen parent artifact
- the mismatch is explained by **numerical device sensitivity** in the neural heuristic inference path:
  - CPU-style rerun reproduces the canonical stored result closely
  - GPU rerun preserves the same qualitative branch ranking and the same misc-repair mechanism, but with shifted exact public expansions

## Merge Decision

- decision: **promote `CX34-A` into the current RS-grounded mainline**
- acceptance scope:
  - accepted on the **public/full-support** axis
  - exact claim numbers stay frozen to `outputs/rs_p0cx34_a_pilot_v1`
  - qualitative robustness is additionally supported by the GPU shadow rerun
- non-claims preserved:
  - no `rs_root_hard_v2/test` hard-test claim
  - no deployable-runtime claim
  - no device-invariant exact-number claim

## Final Mainline Statement

- current accepted RS-grounded mainline: `RS + CX34-A / Subtype-Specific Macro Rescue`
- canonical frozen public numbers:
  - `exp_delta = +420.389`
  - `parasol_misc = +10.500`
  - `maze = 0.0`
  - `flange = +1421.0`
  - `narrow_passage = +99.75`
- follow-up priorities remain:
  - reduce runtime
  - consume hard-test only under a fresh frozen protocol step

## Historical Note

- the fresh frozen hard-test step was later executed in `reports/rs_p0cx34_a_hard_eval_v1.md`
- this recheck audit remains the source of truth for the **public artifact freeze / device-sensitivity diagnosis**, while the hard-eval report is the source of truth for the subsequent frozen hard-test result
