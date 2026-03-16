# P0-CX31 Round1 Summary

- protocol: follow-up stage continuing from `CX29-D / Aux-Calibrated Bridge Threshold`; public-first on `parasol_narrow exp4`; `mp/csm` ordinary-support audit preserved; no hard-test evidence consumed

## Research Anchors
- option / macro preconditions: Ravichandar et al., “Learning Model Preconditions for Planning with Multiple Models”, CoRL 2021 — https://proceedings.mlr.press/v164/ravichandar22a.html
- failure reuse / structured memory: Phillips et al., “The Experience Graph: Leveraging Experience for Planning with Sparse Roadmap Spanners”, ICRA 2012 — https://www.ri.cmu.edu/pub_files/2012/5/icra12.pdf
- reject-option control: Geifman and El-Yaniv, “SelectiveNet: A Deep Neural Network with an Integrated Reject Option”, ICML 2019 — https://proceedings.mlr.press/v97/geifman19a.html
- heuristic depression handling: Hernández, Baier, and Uras, “Depression Avoidance in Real-Time Heuristic Search”, SoCS 2011 — https://ojs.aaai.org/index.php/SOCS/article/view/18315

## Variant Readout
- `CX31-A`: exp4 vs `CX3-D` exp_delta=`401.389`, overhead=`2.468610`, vs parent exp_delta=`0.667`, misc=`2.000`, maze=`0.000`, flange=`0.000`, narrow=`0.000`
- `CX31-B`: exp4 vs `CX3-D` exp_delta=`401.278`, overhead=`2.460467`, vs parent exp_delta=`0.556`, misc=`1.667`, maze=`0.000`, flange=`0.000`, narrow=`0.000`
- `CX31-C`: exp4 vs `CX3-D` exp_delta=`401.444`, overhead=`2.452204`, vs parent exp_delta=`0.722`, misc=`2.167`, maze=`0.000`, flange=`0.000`, narrow=`0.000`

## Interpretation
- `CX31-A` shows that adding `path_openness` to the bridge gate is helpful and beats `CX29-D`, but it is not the strongest structure cue.
- `CX31-B` confirms that a small auxiliary trigger tree can recover some signal, yet still underperforms hand-crafted structural gating.
- `CX31-C / Low-Bridge + Focus Gate` is the best branch. It lifts `parasol_misc` from `-53.667` to `-51.500`, increases public `exp_delta` from `+400.722` to `+401.444`, and preserves `maze = 0.0`, `flange = +1428.4`, and `narrow_passage = +98.25`.
- Shared lesson: the remaining misc improvement continues to come from a tighter `forward_turn` initiation set. The most useful extra feature so far is `focus_gap` paired with a very low `bridge_diffuse` regime.

## Ordering
- rank 1: `CX31-C`
- rank 2: `CX31-A`
- rank 3: `CX31-B`

## Verdict
- `CX31` still does not eliminate the `parasol_misc` deficit, but it advances the best public point again: `-53.667 -> -51.500`.
- The current best follow-up object is `CX31-C`, implemented in `rs_cx30/cx30_c_lbf.py`.
- The next step should keep refining the initiation set for `forward_turn`; there is still no evidence that more global arbitration or heavier online review is the correct lever.
