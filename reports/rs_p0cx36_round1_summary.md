# P0-CX36 Round1 Summary

- protocol: frozen `CX35-B` parent on public evidence; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit
- objective: push the `CX35-B` line from a representation-level typed macro family into a **functionally active structural trigger + counterfactual contract** system

## Research Anchors
- Model preconditions / structural applicability: Ravichandar et al., CoRL 2021 — https://proceedings.mlr.press/v164/ravichandar22a.html
- Experience reuse / planning structure: Phillips et al., ICRA 2012 — https://www.ri.cmu.edu/pub_files/2012/5/icra12.pdf
- Selective prediction / abstention: Geifman and El-Yaniv, ICML 2019 — https://proceedings.mlr.press/v97/geifman19a.html
- Depression avoidance / event-triggered search control: Hernández et al., SoCS 2011 — https://ojs.aaai.org/index.php/SOCS/article/view/18315

## Variant Readout
- `CX36-A`: exp4 vs `CX3-D` exp_delta=`412.722`, overhead=`2.496697`, vs parent exp_delta=`-10.000`, misc=`-30.000`, maze=`0.000`, flange=`0.000`, narrow=`0.000`
- `CX36-B`: exp4 vs `CX3-D` exp_delta=`422.722`, overhead=`1.383060`, vs parent exp_delta=`0.000`, misc=`0.000`, maze=`0.000`, flange=`0.000`, narrow=`0.000`

## Interpretation
- `CX36-A` wires the trigger/review through the real local state plus a support-derived contract, but this immediately drops below `CX35-B` through `parasol_misc`. The trigger/review object is not discriminative enough.
- `CX36-B` switches to a backward-compatible event-triggered extension: preserve the accepted in-slice behavior exactly, and only allow typed family expansion outside the accepted slice under an event gate plus event contract.
- `CX36-B` successfully preserves the entire public family pattern of `CX35-B` while cutting runtime sharply (`2.458320 -> 1.383060` vs `CX3-D` baseline accounting).
- But both `No-Event-Trigger` and `No-Event-Contract` remain effectively tied with `CX36-B` on public expansions. That means the new event-triggered mechanism is still mostly inactive on the benchmark, so the round still does **not** reach fully general mechanization.

## Audit
- ordinary-support invariance still holds:
  - `CX36-A` / `mp,csm`: `max_abs_field_diff = 0.0`
  - `CX36-B` / `mp,csm`: `max_abs_field_diff = 0.0`
- no hard-test evidence was consumed in CX36 because the round did not produce a functionally active trigger/review upgrade over the accepted `CX35-B` parent

## Ordering
- rank 1: `CX36-B`
- rank 2: `CX36-A`

## Verdict
- `CX36` round1 improves the **engineering shape** of the `CX35-B` line, especially runtime, but does not yet complete the desired trigger/review mechanization.
- `CX36-B` is the current best follow-up because it preserves the accepted public pattern while wrapping it in an event-triggered extension.
- The core blocker is now explicit: the trigger/review mechanism still lacks enough positive off-slice training signal to become functionally active rather than merely backward-compatible.
