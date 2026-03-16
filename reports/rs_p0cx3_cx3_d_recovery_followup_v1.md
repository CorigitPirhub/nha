# CX3-D Narrow Recovery Follow-up Note

Status: `rejected-dev-followup`
Date: `2026-03-08`

This note records a **very narrow** `CX3-D` follow-up whose only goal was to reduce the remaining
`narrow_passage` regression without changing the broader method story.

## Attempted change

A small recovery factor was introduced on top of the accepted `CX3-D` line:
- if `bridge_diffuse` is low, `CX3-D` already shrinks its hard edit via `low_bridge_scale`;
- the follow-up added a compensating boost when both:
  - `bridge_diffuse` is low, and
  - `path_openness` is below a threshold,
  with the intent of restoring hard-family gain on the most constrained narrow-passage cases.

This change was deliberately narrow and conservative:
- no new module family;
- no new routing or planner-selection logic;
- only a scene-level scalar recovery multiplier on the existing `CX3-D` perturbation.

## Dev-only evaluation

Evaluation split:
- `rs_root_hard_v2/dev`
- families: `narrow_passage`, `maze`, `deadend_labyrinth`
- 2 cases per family (same dev protocol as the current main trials)

Representative results:

- baseline accepted `CX3-D`-style setting  
  `exp_delta_mean = 129.333`, `success_mean = 0.1667`

- recovery boost `recover_gain = 0.20`, `recover_pathopen_thr = 0.93`  
  `exp_delta_mean = 129.333`, `success_mean = 0.1667`

- recovery boost `recover_gain = 0.35`, `recover_pathopen_thr = 0.94`  
  `exp_delta_mean = 129.333`, `success_mean = 0.1667`

Interpretation:
- the recovery term did **not** improve dev expansion gain at all;
- the score remained flat on the metric we care about;
- therefore this follow-up failed the “hard-family gain amplification” objective already at the dev stage.

## Decision

This follow-up is rejected and is **not** part of the accepted `CX3-D` evidence bundle.
The accepted `CX3-D` line remains the narrower conservative `low_bridge_scale` version summarized in:
- `reports/rs_p0cx3_round1_summary.md`
- `TASK.md`
