# P0-CX27 Round1 Summary

- protocol: frozen `CX23-C / RS-HAA` parent; dev-only trial selection on `calib_hard_v1`; locked public `parasol_narrow exp4` evaluation + `mp/csm` ordinary-support audit; no hard-test evidence consumed

## Research Anchors
- heuristic depression / trap avoidance: Hernández, Baier, and Uras, “Depression Avoidance in Real-Time Heuristic Search”, SoCS 2011 — https://ojs.aaai.org/index.php/SOCS/article/view/18315
- experience-compiled failure reuse: Phillips et al., “The Experience Graph: Leveraging Experience for Planning with Sparse Roadmap Spanners”, ICRA 2012 — https://www.ri.cmu.edu/pub_files/2012/5/icra12.pdf
- abstention as a control primitive: Geifman and El-Yaniv, “SelectiveNet: A Deep Neural Network with an Integrated Reject Option”, ICML 2019 — https://proceedings.mlr.press/v97/geifman19a.html
- learned preconditions / safe delegation: Ravichandar et al., “Learning Model Preconditions for Planning with Multiple Models”, CoRL 2021 — https://proceedings.mlr.press/v164/ravichandar22a.html

## Variant Readout
- `CX27-A`: exp4 vs `CX3-D` exp_delta=`399.167`, overhead=`2.398235`, vs parent exp_delta=`6.278`, maze=`113.000`, misc=`0.000`, flange=`0.000`, narrow=`0.000`
- `CX27-B`: exp4 vs `CX3-D` exp_delta=`392.889`, overhead=`2.550276`, vs parent exp_delta=`0.000`, maze=`0.000`, misc=`0.000`, flange=`0.000`, narrow=`0.000`
- `CX27-C`: exp4 vs `CX3-D` exp_delta=`384.778`, overhead=`2.535617`, vs parent exp_delta=`-8.111`, maze=`110.000`, misc=`0.000`, flange=`-51.000`, narrow=`-0.250`
- `CX27-D`: exp4 vs `CX3-D` exp_delta=`384.722`, overhead=`2.533672`, vs parent exp_delta=`-8.167`, maze=`110.000`, misc=`-0.167`, flange=`-51.000`, narrow=`-0.250`
- `CX27-F`: exp4 vs `CX3-D` exp_delta=`395.833`, overhead=`2.400491`, vs parent exp_delta=`2.944`, maze=`110.000`, misc=`-9.500`, flange=`0.000`, narrow=`0.000`

## Interpretation
- `CX27-A / maze-only depression guard` is the only branch that improves the parent without paying a family-regression tax: it exactly removes the `maze = -113.0` liability and lifts public `exp_delta` from `+392.889` to `+399.167`.
- `CX27-B` proves the original misc dampener was behaviorally inert: selective abstention triggers on some nodes, but it does not change expansions on any public family.
- `CX27-C` and `CX27-D` confirm that broader failure-memory logic can repair maze, but both pay for it by cutting `flange` and slightly harming `narrow_passage`; they are not promotable.
- `CX27-F` shows the strongest combined maze+misc repair attempt still worsens `parasol_misc`, so the current misc problem is not solved by simply escalating from abstain to reverse-setup redirection.
- Shared bottleneck: `maze` is now fixable inside `RS-HAA`, but `parasol_misc` remains a low-support, structure-misaligned tail regime. Direct HAA-side gating can suppress clear maze traps, yet it still lacks a reliable positive alternative policy for misc.

## Ordering
- rank 1: `CX27-A`
- rank 2: `CX27-C`
- rank 3: `CX27-D`
- rank 4: `CX27-F`
- rank 5: `CX27-B`

## Verdict
- `CX27` does not meet the full target. The best branch (`CX27-A`) fixes `maze` while preserving `flange` and `narrow_passage`, but it leaves `parasol_misc` unchanged.
- No branch reaches the requested deployment envelope: all wrappers remain materially slower than the parent `CX23-C`.
- The evidence is still useful: the `maze` failure is now isolated as a repairable HAA-side depression/commit problem, while `parasol_misc` looks like a missing-alternative-policy problem rather than a pure over-commit problem.
