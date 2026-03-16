# P0-CX32 Round1 Summary

- protocol: frozen `CX30-C / Low-Bridge + Focus Gate` parent; dev-only trial selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; no hard-test evidence consumed

## Research Anchors
- option / macro preconditions: Ravichandar et al., “Learning Model Preconditions for Planning with Multiple Models”, CoRL 2021 — https://proceedings.mlr.press/v164/ravichandar22a.html
- failure reuse / structured memory: Phillips et al., “The Experience Graph: Leveraging Experience for Planning with Sparse Roadmap Spanners”, ICRA 2012 — https://www.ri.cmu.edu/pub_files/2012/5/icra12.pdf
- reject-option control: Geifman and El-Yaniv, “SelectiveNet: A Deep Neural Network with an Integrated Reject Option”, ICML 2019 — https://proceedings.mlr.press/v97/geifman19a.html
- heuristic depression handling: Hernández, Baier, and Uras, “Depression Avoidance in Real-Time Heuristic Search”, SoCS 2011 — https://ojs.aaai.org/index.php/SOCS/article/view/18315

## Variant Readout
- `CX32-A`: exp4 vs `CX3-D` exp_delta=`404.389`, overhead=`2.470546`, vs parent exp_delta=`2.944`, misc=`8.833`, maze=`0.000`, flange=`0.000`, narrow=`0.000`
- `CX32-B`: exp4 vs `CX3-D` exp_delta=`407.333`, overhead=`2.421963`, vs parent exp_delta=`5.889`, misc=`17.667`, maze=`0.000`, flange=`0.000`, narrow=`0.000`

## Failure Slices
- `sample_000000`: current best repair comes from suppressing `escape_border|reverse` in the mid-bridge / low-focus / high-path-openness slice; this alone recovers `+84` expansions versus `CX30-C`.
- `sample_000001`: a distinct subtype exists — very low bridge + very high focus + very open path — where a **budgeted reverse rescue** from `uncertain|none` helps; with the budgeted slice repair it recovers `+22`.
- `sample_000006`: still uses the old low-bridge / low-focus `forward_turn` gate and stays improved.
- `sample_000007`: remains the main unsolved stubborn case; none of the current macro-language switches improve it materially.

## Interpretation
- `CX32-A / dual-slice repair` already shows that the residual misc failure is not monolithic: a single extra gate for the mid-bridge escape slice meaningfully reduces `parasol_misc`.
- `CX32-B / budgeted slice repair` is the best branch. It adds one more root-cause-specific rule — a budgeted reverse rescue for the high-focus / low-bridge misc subtype — and this pushes `parasol_misc` from `-51.500` to `-33.833`.
- This is the first stage where misc improves by a **large** amount rather than a marginal amount, and it happens without giving up `maze = 0.0`, `flange = +1428.4`, or `narrow_passage = +98.25`.
- The remaining obstacle is now even narrower: `sample_000007` dominates the leftover misc deficit, which suggests the next improvement needs a new action language or a different structural witness for that subtype.

## Ordering
- rank 1: `CX32-B`
- rank 2: `CX32-A`

## Verdict
- `CX32` is the strongest misc-repair stage so far. Best branch `CX32-B` moves:
  - public `exp_delta`: `+401.444 -> +407.333`
  - `parasol_misc`: `-51.500 -> -33.833`
- `CX32-B` still does not solve misc completely, but it changes the picture from “small nudges” to “substantial structural repair”.
- The next follow-up should target the remaining stubborn `sample_000007` subtype specifically; the other large misc liabilities are now partially neutralized.
