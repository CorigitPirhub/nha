# P0-CX29 Round1 Summary

- protocol: frozen `CX28-D / Misc Forward-Turn Arbitration` parent; dev-only trial selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; no hard-test evidence consumed

## Research Anchors
- option / macro preconditions: Ravichandar et al., “Learning Model Preconditions for Planning with Multiple Models”, CoRL 2021 — https://proceedings.mlr.press/v164/ravichandar22a.html
- failure reuse / structured memory: Phillips et al., “The Experience Graph: Leveraging Experience for Planning with Sparse Roadmap Spanners”, ICRA 2012 — https://www.ri.cmu.edu/pub_files/2012/5/icra12.pdf
- reject-option control: Geifman and El-Yaniv, “SelectiveNet: A Deep Neural Network with an Integrated Reject Option”, ICML 2019 — https://proceedings.mlr.press/v97/geifman19a.html
- heuristic depression handling: Hernández, Baier, and Uras, “Depression Avoidance in Real-Time Heuristic Search”, SoCS 2011 — https://ojs.aaai.org/index.php/SOCS/article/view/18315

## Variant Readout
- `CX29-A`: exp4 vs `CX3-D` exp_delta=`399.167`, overhead=`1.403115`, vs parent exp_delta=`-1.389`, misc=`-4.167`, maze=`0.000`, flange=`0.000`, narrow=`0.000`
- `CX29-B`: exp4 vs `CX3-D` exp_delta=`400.222`, overhead=`1.320480`, vs parent exp_delta=`-0.333`, misc=`-1.000`, maze=`0.000`, flange=`0.000`, narrow=`0.000`
- `CX29-C`: exp4 vs `CX3-D` exp_delta=`400.722`, overhead=`1.361321`, vs parent exp_delta=`0.167`, misc=`0.500`, maze=`0.000`, flange=`0.000`, narrow=`0.000`
- `CX29-D`: exp4 vs `CX3-D` exp_delta=`400.722`, overhead=`2.444993`, vs parent exp_delta=`0.167`, misc=`0.500`, maze=`0.000`, flange=`0.000`, narrow=`0.000`

## Interpretation
- `CX29-A / multi-step rollout review` proves that heavier online review is not enough by itself: it actually drops behind the `CX28-D` parent on misc.
- `CX29-B / forward-turn blend` narrows the damage versus `CX29-A`, but still underperforms the parent; simply adding straight fallback inside the turn option is not sufficient.
- `CX29-C / bridge-calibrated forward-turn` is the first true improvement over `CX28-D`: it lifts `parasol_misc` from `-54.167` to `-53.667` while preserving `maze = 0.0`, `flange = +1428.4`, and `narrow_passage = +98.25`.
- `CX29-D / aux-calibrated bridge threshold` reaches the same public improvement as `CX29-C`, but does so with a cleaner protocol story because the bridge threshold is selected from non-public `rs_root_hard_v2/dev` misc cases.
- The bottleneck is now very narrow: misc repair is dominated by whether `forward_turn` is invoked under the right bridge-diffuse regime. Broader review logic and blend logic add cost without adding signal.

## Ordering
- rank 1: `CX29-D`
- rank 2: `CX29-C`
- rank 3: `CX29-B`
- rank 4: `CX29-A`

## Verdict
- `CX29` still does not hit the requested endpoint, but it does advance the line: best `parasol_misc` improves from `-54.167` to `-53.667`, and public `exp_delta` rises from `+400.556` to `+400.722`, with all protected families preserved.
- `CX29-D` is the preferred follow-up branch because it matches the best public result while using non-public auxiliary misc cases for threshold calibration.
- The next follow-up should continue on bridge/structure-calibrated `forward_turn` triggering; there is no evidence that heavier local review or broader option blending is the right lever.
