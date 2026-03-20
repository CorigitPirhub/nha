# P0-CX33 Round1 Summary

- protocol: frozen `CX32-B / Budgeted Slice Repair` parent; dev-only trial selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; no hard-test evidence consumed

## Research Anchors
- option / macro preconditions: Ravichandar et al., “Learning Model Preconditions for Planning with Multiple Models”, CoRL 2021 — https://proceedings.mlr.press/v164/ravichandar22a.html
- failure reuse / structured memory: Phillips et al., “The Experience Graph: Leveraging Experience for Planning with Sparse Roadmap Spanners”, ICRA 2012 — https://www.ri.cmu.edu/pub_files/2012/5/icra12.pdf
- reject-option control: Geifman and El-Yaniv, “SelectiveNet: A Deep Neural Network with an Integrated Reject Option”, ICML 2019 — https://proceedings.mlr.press/v97/geifman19a.html
- heuristic depression handling: Hernández, Baier, and Uras, “Depression Avoidance in Real-Time Heuristic Search”, SoCS 2011 — https://ojs.aaai.org/index.php/SOCS/article/view/18315

## Variant Readout
- `CX33-A`: exp4 vs `CX3-D` exp_delta=`408.500`, overhead=`2.087175`, vs parent exp_delta=`1.167`, misc=`8.667`, maze=`0.000`, flange=`-7.400`, narrow=`1.500`
- `CX33-B`: exp4 vs `CX3-D` exp_delta=`411.444`, overhead=`3.504408`, vs parent exp_delta=`4.111`, misc=`17.500`, maze=`0.000`, flange=`-7.400`, narrow=`1.500`

## Interpretation
- `CX33-A` is the first branch that injects a dedicated repair slice for the previously stubborn `sample_000007` regime by redirecting a subset of `uncertain|none` states into `forward_turn`.
- `CX33-B` is stronger: it keeps the budgeted rescue logic from `CX32-B` and adds the stubborn-slice turn repair, pushing `parasol_misc` from `-33.833` to `-16.333`.
- This is the first stage where the misc deficit is mostly concentrated in a handful of cases rather than spread broadly across the family.
- The tradeoff is now explicit: the new stubborn-slice repair slightly leaks into flange-like states, producing a small `flange` regression (`-7.4`) while keeping `maze = 0.0` and slightly improving `narrow_passage`.

## Ordering
- rank 1: `CX33-B`
- rank 2: `CX33-A`

## Verdict
- `CX33` is the strongest misc-repair stage so far: `parasol_misc` improves from `-33.833` to `-16.333`, and public `exp_delta` rises from `+407.333` to `+411.444`.
- It still does not satisfy the target contract because the misc gain comes with a small but non-zero `flange` tax.
- The next follow-up should preserve the new `sample_000007` repair slice while tightening family scoping so the intervention cannot leak into flange-like states.
