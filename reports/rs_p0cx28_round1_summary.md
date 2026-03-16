# P0-CX28 Round1 Summary

- protocol: frozen `CX27-A / Maze Depression Guard` parent; dev-only trial selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; no hard-test evidence consumed

## Research Anchors
- option / macro preconditions: Ravichandar et al., “Learning Model Preconditions for Planning with Multiple Models”, CoRL 2021 — https://proceedings.mlr.press/v164/ravichandar22a.html
- failure reuse / structured memory: Phillips et al., “The Experience Graph: Leveraging Experience for Planning with Sparse Roadmap Spanners”, ICRA 2012 — https://www.ri.cmu.edu/pub_files/2012/5/icra12.pdf
- reject-option control: Geifman and El-Yaniv, “SelectiveNet: A Deep Neural Network with an Integrated Reject Option”, ICML 2019 — https://proceedings.mlr.press/v97/geifman19a.html
- heuristic depression handling: Hernández, Baier, and Uras, “Depression Avoidance in Real-Time Heuristic Search”, SoCS 2011 — https://ojs.aaai.org/index.php/SOCS/article/view/18315

## Variant Readout
- `CX28-A`: exp4 vs `CX3-D` exp_delta=`397.056`, overhead=`2.614938`, vs parent exp_delta=`-2.111`, misc=`-6.333`, maze=`0.000`, flange=`0.000`, narrow=`0.000`
- `CX28-B`: exp4 vs `CX3-D` exp_delta=`397.056`, overhead=`2.601315`, vs parent exp_delta=`-2.111`, misc=`-6.333`, maze=`0.000`, flange=`0.000`, narrow=`0.000`
- `CX28-C`: exp4 vs `CX3-D` exp_delta=`392.611`, overhead=`2.593292`, vs parent exp_delta=`-6.556`, misc=`-19.667`, maze=`0.000`, flange=`0.000`, narrow=`0.000`
- `CX28-D`: exp4 vs `CX3-D` exp_delta=`400.556`, overhead=`2.430974`, vs parent exp_delta=`1.389`, misc=`4.167`, maze=`0.000`, flange=`0.000`, narrow=`0.000`
- `CX28-E`: exp4 vs `CX3-D` exp_delta=`399.778`, overhead=`2.504000`, vs parent exp_delta=`0.611`, misc=`1.833`, maze=`0.000`, flange=`0.000`, narrow=`0.000`

## Interpretation
- `CX28-A` and `CX28-B` show that generic misc local review / class-precondition switching still overfires on the long tail and makes `parasol_misc` worse by `-6.333`; pure local review is not enough.
- `CX28-C` confirms the main failure mode: broader scene-conditioned arbitration can push the wrong reverse-style language into misc and collapse the worst case.
- `CX28-D / forward-turn arbitration` is the best branch. It improves `parasol_misc` from `-58.333` to `-54.167`, keeps `maze = 0.0`, `flange = +1428.4`, and `narrow_passage = +98.25`, and slightly lifts overall public `exp_delta`.
- `CX28-E / bridge-filtered forward-turn` is a safer refinement. It still improves `parasol_misc`, but only to `-56.500`, which means the extra filter removes both bad and good interventions.
- Main lesson: `parasol_misc` is not fixed by abstention or reverse redirection. The only positive signal comes from a **forward-turn alternative macro language**, so the remaining bottleneck is a better trigger/precondition for when to swap from `forward_safe|straight` to `forward_safe|forward_turn`.

## Ordering
- rank 1: `CX28-D`
- rank 2: `CX28-E`
- rank 3: `CX28-A`
- rank 4: `CX28-B`
- rank 5: `CX28-C`

## Verdict
- `CX28` still does not meet the full target. No branch fully fixes `parasol_misc`, and every wrapper remains slower than the `CX27-A` parent.
- The best branch is `CX28-D`: it gives a real but limited misc repair (`+4.167` vs parent) while exactly preserving the protected families.
- The next follow-up should stay on the `forward-turn alternative macro language` line and improve trigger calibration, rather than revisiting abstention-only or reverse-family repairs.
