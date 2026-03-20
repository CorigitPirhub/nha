# P0-CX34 Round1 Summary

- protocol: frozen `CX33-B / Budgeted Stubborn-Slice Repair` parent; dev-only selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; no hard-test evidence consumed

## Research Anchors
- option / macro preconditions: Ravichandar et al., “Learning Model Preconditions for Planning with Multiple Models”, CoRL 2021 — https://proceedings.mlr.press/v164/ravichandar22a.html
- failure reuse / structured memory: Phillips et al., “The Experience Graph: Leveraging Experience for Planning with Sparse Roadmap Spanners”, ICRA 2012 — https://www.ri.cmu.edu/pub_files/2012/5/icra12.pdf
- reject-option control: Geifman and El-Yaniv, “SelectiveNet: A Deep Neural Network with an Integrated Reject Option”, ICML 2019 — https://proceedings.mlr.press/v97/geifman19a.html
- heuristic depression handling: Hernández, Baier, and Uras, “Depression Avoidance in Real-Time Heuristic Search”, SoCS 2011 — https://ojs.aaai.org/index.php/SOCS/article/view/18315
- motion-primitive adaptation: Pivtoraiko and Kelly, “Efficient constrained path planning via search in state lattices”, iSAIRAS 2005 / related motion primitive work

## Variant Readout
- `CX34-A`: exp4 vs `CX3-D` exp_delta=`420.389`, overhead=`3.527234`, vs parent exp_delta=`8.944`, misc=`26.833`, maze=`0.000`, flange=`0.000`, narrow=`0.000`

## Interpretation
- `CX34-A / Subtype-Specific Macro Rescue` adds a new mechanism-level object that was missing in prior stages: a **custom reverse macro language** for the low-bridge / mid-focus / high-openness misc subtype.
- This directly repairs `sample_000006`, which had remained stuck at `-46` under `CX33-B`. With the new macro rescue it flips to a strong positive case (`+115` vs `CX3-D`), contributing `+161` expansions relative to `CX33-B`.
- Unlike the `CX33` stubborn-slice turn repair, this new rescue does **not** tax `flange`; `maze`, `flange`, and `narrow_passage` all stay unchanged relative to the parent.
- Most importantly, `parasol_misc` crosses zero for the first time on the public set: `-16.333 -> +10.500`.
- The remaining unresolved misc liability is now concentrated in `sample_000000` and `sample_000001` (and a small residual in `sample_000007`), rather than being a family-wide issue.

## Verdict
- `CX34-A` is the first branch on this line that eliminates the average `parasol_misc` deficit while preserving the protected families.
- It still carries a large runtime burden (`~3.53x` vs `CX3-D`), so it is not yet a clean deployable mainline.
- But it is the strongest structural result so far and materially changes the situation: misc is no longer the dominant negative family on public evidence.
