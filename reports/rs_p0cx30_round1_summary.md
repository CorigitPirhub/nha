# P0-CX30 Round1 Summary

- protocol: frozen `CX29-D / Aux-Calibrated Bridge Threshold` parent; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; no hard-test evidence consumed

## Research Anchors
- option / macro preconditions: Ravichandar et al., “Learning Model Preconditions for Planning with Multiple Models”, CoRL 2021 — https://proceedings.mlr.press/v164/ravichandar22a.html
- failure reuse / structured memory: Phillips et al., “The Experience Graph: Leveraging Experience for Planning with Sparse Roadmap Spanners”, ICRA 2012 — https://www.ri.cmu.edu/pub_files/2012/5/icra12.pdf
- reject-option control: Geifman and El-Yaniv, “SelectiveNet: A Deep Neural Network with an Integrated Reject Option”, ICML 2019 — https://proceedings.mlr.press/v97/geifman19a.html
- heuristic depression handling: Hernández, Baier, and Uras, “Depression Avoidance in Real-Time Heuristic Search”, SoCS 2011 — https://ojs.aaai.org/index.php/SOCS/article/view/18315

## Variant Readout
- `CX30-A`: exp4 vs `CX3-D` exp_delta=`401.389`, overhead=`2.468610`, vs parent exp_delta=`0.667`, misc=`2.000`, maze=`0.000`, flange=`0.000`, narrow=`0.000`
- `CX30-B`: exp4 vs `CX3-D` exp_delta=`401.278`, overhead=`2.460467`, vs parent exp_delta=`0.556`, misc=`1.667`, maze=`0.000`, flange=`0.000`, narrow=`0.000`
- `CX30-C`: exp4 vs `CX3-D` exp_delta=`401.444`, overhead=`2.452204`, vs parent exp_delta=`0.722`, misc=`2.167`, maze=`0.000`, flange=`0.000`, narrow=`0.000`

## Interpretation
- `CX30-A / path-openness refined gate` improves over `CX29-D` by isolating a very narrow extra misc regime; it gains `+2.000` on `parasol_misc` without touching the protected families.
- `CX30-B / aux trigger tree` also improves over the parent, but less than `CX30-A`; the event-level tree does recover some misc signal, yet it is weaker than the hand-crafted structural gate.
- `CX30-C / low-bridge + focus-gap gate` is the best branch. It improves `parasol_misc` from `-53.667` to `-51.500`, raises public `exp_delta` from `+400.722` to `+401.444`, and keeps `maze = 0.0`, `flange = +1428.4`, and `narrow_passage = +98.25`.
- Shared lesson: the surviving misc gain still comes from a tighter `forward_turn` initiation set, not from heavier review or more global arbitration. The most useful additional feature so far is `focus_gap` paired with a low `bridge_diffuse` trigger.

## Ordering
- rank 1: `CX30-C`
- rank 2: `CX30-A`
- rank 3: `CX30-B`

## Verdict
- `CX30` still does not solve `parasol_misc`, but it advances the best public point again: `-53.667 -> -51.500`.
- The current best branch is `CX30-C / Low-Bridge + Focus Gate`.
- The next follow-up should continue to refine the initiation set for `forward_turn`; the remaining problem looks like a narrow structural trigger issue, not a missing macro family issue.
