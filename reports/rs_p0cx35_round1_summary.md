# P0-CX35 Round1 Summary

- protocol: frozen `CX34-A` parent on public evidence; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit
- objective: push `CX34-A / Subtype-Specific Macro Rescue` from a patch-adjacent singleton rescue toward a more mechanized macro-language object without losing the accepted public/hard conclusion

## Research Anchors
- Experience reuse / reusable planning structure: Phillips et al., “The Experience Graph”, ICRA 2012 — https://www.ri.cmu.edu/pub_files/2012/5/icra12.pdf
- Model preconditions / option applicability: Ravichandar et al., “Learning Model Preconditions for Planning with Multiple Models”, CoRL 2021 — https://proceedings.mlr.press/v164/ravichandar22a.html
- Motion primitives / state lattices: Pivtoraiko and Kelly, iSAIRAS 2005
- Maneuver automata / typed maneuver objects: Schouwenaars et al., ACC 2001 / hybrid maneuver-automata line

## Variant Readout
- `CX35-A`: exp4 vs `CX3-D` exp_delta=`353.722`, overhead=`3.428553`, vs parent exp_delta=`-66.667`, misc=`-28.167`, maze=`0.000`, flange=`7.400`, narrow=`-267.000`
- `CX35-B`: exp4 vs `CX3-D` exp_delta=`422.722`, overhead=`2.458320`, vs parent exp_delta=`2.333`, misc=`1.833`, maze=`0.000`, flange=`7.400`, narrow=`-1.500`
- `CX35-C`: exp4 vs `CX3-D` exp_delta=`355.222`, overhead=`3.481344`, vs parent exp_delta=`-65.167`, misc=`-28.167`, maze=`0.000`, flange=`7.400`, narrow=`-260.250`

## Hard Eval
- `CX35-B` hard-test report: `reports/rs_p0cx35_b_hard_eval_v1.md`
- `CX35-B` vs `CX3-D` on `rs_root_hard_v2/test`: success_delta_pp=`+2.740`, exp_delta=`+196.548`, mean_time_overhead_ratio=`2.562212`, path_delta=`-1.179`
- reading: `CX35-B` preserves the accepted `CX34-A` hard-test conclusion almost exactly, with a small runtime improvement, but does not yet fix the hard-family negatives on `deadend_labyrinth`, `flange`, and `parasol_misc`

## Interpretation
- `CX35-A` proves that a direct support-band witness over typed macro families is too aggressive: it destroys the accepted public misc and narrow pattern even though the macro-family object itself is not obviously wrong.
- `CX35-B` is the best result of the round: it keeps the accepted `CX34-A` slice, replaces the singleton `(9,9)` macro with a typed reverse-pair family, preserves the public/hard conclusion, and slightly reduces runtime.
- `CX35-C` shows that expanding the typed family outside the accepted slice via the current witness logic immediately reintroduces the same false-trigger failure mode seen in `CX35-A`.
- The key structural lesson is now sharper: the macro object can be family-typed, but the trigger/review mechanism is still not mechanized enough.

## Ordering
- rank 1: `CX35-B`
- rank 2: `CX35-A`
- rank 3: `CX35-C`

## Verdict
- `CX35` round1 does **not** replace the accepted mainline.
- `CX35-B` is the current best mechanization follow-up because it upgrades the action object from a singleton custom macro to a typed reverse-pair family while keeping the accepted public/hard result.
- But the `No-Typed-Family-Choice` ablation is effectively tied with `CX35-B`, so the benchmark is still exercising only the original effective family member. This means the round achieves **representation-level mechanization**, not yet **full functional mechanization**.
