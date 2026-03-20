# P0-CX37 Round1 Summary

- protocol: frozen `CX36-B` parent on public evidence; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit
- objective: turn the replay-positive trigger signal from `CX37-A` into a functionally active **review scheduler / priority prior**

## Research Anchors
- Ross et al., “A Reduction of Imitation Learning and Structured Prediction to No-Regret Online Learning”, AISTATS 2011 — https://proceedings.mlr.press/v15/ross11a/ross11a.pdf
- Retrospective imitation / search-state replay — https://arxiv.org/abs/1804.00846
- Ravichandar et al., “Learning Model Preconditions for Planning with Multiple Models”, CoRL 2021 — https://proceedings.mlr.press/v164/ravichandar22a.html
- Moore and Atkeson, “Prioritized Sweeping”, NIPS 1992 — https://proceedings.neurips.cc/paper_files/paper/1992/file/55743cc0393b1cb4b8b37d09ae48d097-Paper.pdf

## Variant Readout
- `CX37-A`: exp4 vs `CX3-D` exp_delta=`422.722`, overhead=`2.509557`, vs parent exp_delta=`0.000`, misc=`0.000`, maze=`0.000`, flange=`0.000`, narrow=`0.000`
- `CX37-B`: exp4 vs `CX3-D` exp_delta=`422.722`, overhead=`2.526984`, vs parent exp_delta=`0.000`, misc=`0.000`, maze=`0.000`, flange=`0.000`, narrow=`0.000`

## Interpretation
- `CX37-A` successfully compiled the first nonzero off-slice replay-positive trigger signal (`positive_hits = 236`), but benchmark behavior stayed exactly equal to `CX36-B`.
- `CX37-B` then converted that replay-positive contract from a hard gate into a review scheduler / priority prior, but the public result is still exactly tied with `CX36-B`.
- The ablations make the failure mode explicit:
  - `No-Replay-Prior`: same expansions, slightly higher runtime
  - `No-Replay-Scheduler`: same expansions, slightly lower runtime
- So the replay-based scheduler is still not functionally active; it currently adds bookkeeping cost without changing search decisions on the public benchmark.

## Audit
- ordinary-support invariance still holds:
  - `CX37-A` / `mp,csm`: `max_abs_field_diff = 0.0`
  - `CX37-B` / `mp,csm`: `max_abs_field_diff = 0.0`
- no hard-test evidence was consumed in CX37 because neither branch improved over the frozen `CX36-B` parent on public behavior

## Ordering
- rank 1: `CX37-A`
- rank 2: `CX37-B`

## Verdict
- `CX37` does **not** complete the desired fully general mechanization.
- The positive result is representational: replay/off-policy sibling states can now produce nonzero trigger positives.
- The negative result is operational: even when replay-positive signal is converted into a scheduler / priority prior, it still does not alter benchmark behavior.
- The next step is no longer “better gating” or “more priority bias”; it is to redesign the review target so replay-positive states enter a bounded local review with measurable activation, rather than merely a passive prior.
