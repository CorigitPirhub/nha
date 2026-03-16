# P0-CX-2 Design Scout V1

Status: `research-complete / candidate-frozen`
Date: `2026-03-08`

This note documents the **second-round design scouting** for `P0-CX` after the first `CX-A/B/C/D`
round failed to establish a hard advantage axis on the frozen public `parasol_narrow` protocol.

Implementation follow-up for the frozen `CX2-*` family is now recorded in `reports/rs_p0cx2_round1_summary.md`.

## 1. Why `CX-A/B/C/D` were insufficient

Round-1 evidence root:
- `reports/rs_p0cx_round1_summary.md`
- `outputs/rs_p0cx_round1_summary/summary.csv`

The failure pattern is now clear:
1. the first-round candidates only changed the **amplitude / mixture / local gating** of the existing residual field;
2. they produced at most small same-`alpha` expansion gains on public parasol, but **no success recovery**;
3. therefore the structural bottleneck is unlikely to be “residual strength is slightly wrong”, and more likely to be one of:
   - missing **global corridor / passage structure**;
   - missing **dead-end exclusion / separator awareness**;
   - missing **geometry-level field deformation**, rather than local residual rescaling;
   - missing **path-integral / nonlocal trade-off** between route length and corridor capacity.

This means `P0-CX-2` should not be another local multiplicative tweak. It should directly modify the
`RS field -> heuristic field -> planner guidance` chain at the **geometry / topology / global-field** level.

## 2. Literature clusters consulted

Only primary sources are listed below.

### 2.1 Differentiable search and search-aware heuristic learning

1. `Path Planning using Neural A* Search` — ICML 2021  
   https://proceedings.mlr.press/v139/yonetani21a.html  
   Key takeaway: learned modules can act directly on the **search guidance object**, not only on final path regression.

2. `Neural Weighted A*: Learning Graph Costs and Heuristics with Differentiable Anytime A*` — 2021  
   https://arxiv.org/abs/2105.01480  
   Key takeaway: jointly shaping heuristic behavior and search trade-offs is stronger than post-hoc scoring.

3. `A Differentiable Loss Function for Learning Heuristics in A*` — 2022  
   https://arxiv.org/abs/2209.05206  
   Key takeaway: if the goal is reducing excessive expansions, plain regression is mismatched; the loss should target **search errors**.

4. `Learning heuristics for A*` — ICLR 2022 GroundedML Workshop  
   https://arxiv.org/abs/2204.08938  
   Key takeaway: consistent / structured heuristic targets matter when plugging learned values into classical search.

### 2.2 PDE / operator / neural-field motion planning

5. `NTFields: Neural Time Fields for Physics-Informed Robot Motion Planning` — ICLR 2023  
   https://openreview.net/forum?id=Q1UuJzA3tS  
   Key takeaway: arrival-time / Eikonal fields provide a global planning object, and bidirectional field following can expose path structure beyond pointwise value regression.

6. `Progressive Learning for Physics-informed Neural Motion Planning` — RSS 2023  
   https://www.roboticsproceedings.org/rss19/p063.html  
   Key takeaway: in narrow-passage settings, learning the right field parameterization and curriculum matters more than just adding capacity.

7. `Generalizable Motion Planning via Operator Learning` — ICLR 2025  
   https://openreview.net/forum?id=UYcUpiULmT  
   Key takeaway: learning a value-field operator with structural inductive bias can yield `ϵ`-consistent heuristics; obstacle erosion can improve heuristic consistency.

### 2.3 Topology / passage / subgoal / separator structure

8. `Learning over Subgoals for Efficient Navigation of Structured, Unknown Environments` — CoRL 2018  
   https://proceedings.mlr.press/v87/stein18a.html  
   Key takeaway: avoiding dead-ends requires reasoning over **structured long-horizon subgoal effects**, not only local obstacle cues.

9. `Finding Options that Minimize Planning Time` — ICML 2019  
   https://proceedings.mlr.press/v97/jinnai19a.html  
   Key takeaway: bottleneck states and shortest-path betweenness are strong proxies for planning-time reduction.

10. `Learning Proofs of Motion Planning Infeasibility` — RSS 2021  
    https://www.roboticsproceedings.org/rss17/p064.html  
    Key takeaway: separating manifolds / closed obstacle-region certificates provide a principled way to reason about **where planning should not go**.

11. `Identification and Representation of Homotopy Classes of Trajectories for Search-based Path Planning in 3D` — RSS 2011  
    https://www.roboticsproceedings.org/rss07/p02.html  
    Key takeaway: line integrals over specially constructed fields can encode homotopy-class information useful to search.

12. `Passage-aware Optimal Path Planning Compatible with Sampling-based Planners` — RSS 2024  
    https://www.roboticsproceedings.org/rss20/p039.html  
    Key takeaway: a strong planner should explicitly trade off **path length** and **accessible free space along the path**, rather than using local clearance alone.

13. `GraphMP: Graph Neural Network-based Motion Planning with Efficient Graph Search` — NeurIPS 2023  
    https://papers.nips.cc/paper_files/paper/2023/file/096961cae3c3423c44ea045aeb584e05-Paper-Conference.pdf  
    Key takeaway: the gain often comes from coupling learned global pattern extraction with actual search mechanics, not replacing search altogether.

## 3. Design principles distilled for `P0-CX-2`

The above literature suggests four principles for the next round:

1. **No more local-only gain scheduling.**  
   Round-1 already showed that local rescaling of the residual amplitude is too weak.

2. **Act on global geometry / topology, not just pixelwise residual magnitude.**  
   New modules should reshape the effective planning medium, corridor structure, or separator structure.

3. **Make the hard-scene advantage come from a field-level object that is independently discussable.**  
   Each new module should be intelligible as a standalone planning idea, not a pile of heuristics.

4. **Use search-aware supervision as a shared training rule.**  
   Even if a candidate changes the field representation, it should still be trained / selected with hard-family search-effort signals, not only L2 field fitting.

## 4. Frozen `P0-CX-2` candidates

Below, all candidates preserve the core pipeline:

`occupancy + start/goal -> RS analytical field -> CX2 module -> fused heuristic field -> same planner`

They do **not** jump to router / portfolio / policy-selection lines.

### CX2-A — `RS-MDE` (RS Morphological Deformation Envelope)

Type: `needs new base-model module`

Core idea:
1. learn a **state-conditioned morphology field** `ρ(x, y)` that locally decides where the obstacle geometry should be slightly eroded or dilated;
2. construct two surrogate media:
   - optimistic medium `Ω^-_ρ` (locally eroded);
   - conservative medium `Ω^+_ρ` (locally dilated);
3. compute exact or semi-exact `RS` fields on the two media, giving an envelope:
   - `V^-_RS(x)` on `Ω^-_ρ`;
   - `V^+_RS(x)` on `Ω^+_ρ`;
4. use the envelope width `ΔV_ρ = V^+_RS - V^-_RS` as a trust signal, and fuse it with the current residual field.

Why this is not a copy of existing work:
- unlike the global obstacle erosion trick in PNO, this is **local, start-goal-conditioned, and RS-native**;
- unlike `CX-A`, it does not widen a residual tube; it **deforms the planning geometry itself**.

Why it may solve the current structural issue:
- the failure mode is likely not “residual strength is slightly wrong”, but “the wrong geometric medium is being searched”;
- morphology-level deformation can open the right corridor or close a misleading side-pocket **before** residual fusion.

Theory hook:
- obstacle monotonicity implies a bracket of the true cost field:
  `V^-_ρ <= V* <= V^+_ρ`;
- when `ΔV_ρ` is small, the medium is structurally stable and the learned field can be trusted more;
- when `ΔV_ρ` is large, planner trust should fall back toward plain `RS`.

### CX2-B — `RS-HBF` (RS Harmonic Bridge Field)

Type: `needs new base-model module`

Core idea:
1. detect a sparse set of candidate gates / passage anchors from occupancy, `RS` isocontours, and hard-family geometry cues;
2. build a small set of **harmonic bridge basis fields** `{φ_k}` on free space, each connecting meaningful anchor pairs (start-goal, start-gate, gate-goal);
3. learn only the coefficients / gate weights, and inject the resulting bridge field into the heuristic:
   `h = h_RS + r + Σ_k a_k φ_k`.

Why this is not a copy:
- unlike subgoal planners, it does not change the action space or planner topology;
- unlike `CX-B`, it is not a pointwise gate; it is a **global low-rank field bridge**.

Why it may help:
- local residuals do not seem able to express long-range corridor commitment;
- harmonic bridge modes can impose a smooth global preference for the correct narrow passage.

Theory hook:
- harmonic fields satisfy the maximum principle and minimize Dirichlet energy;
- therefore the bridge field is less likely to create spurious interior minima than arbitrary residual textures;
- bounded coefficients `a_k` imply a bounded perturbation on top of `RS`.

### CX2-C — `RS-BCE` (RS Barrier-Certified Exclusion)

Type: `needs new base-model module`

Core idea:
1. learn a **separator / exclusion field** `b(x, y) >= 0` that marks dead-end basins, disconnected pockets, or states lying behind soft obstacle separators relative to the current start-goal pair;
2. fuse it as a nonnegative exclusion penalty:
   `h = h_RS + r + λ b`;
3. optionally gate `b` by positive corridor evidence so that truly traversable narrow passages are not overly penalized.

Why this is not a copy:
- unlike RSS 2021 infeasibility-proof learning, this is not a proof-producing planner;
- it turns separator structure into a **search guidance field**, which remains compatible with the current `RS` backbone and planner.

Why it may help:
- public parasol failures suggest that some states still look deceptively attractive although they belong to bad pockets;
- a negative certificate field can suppress those pockets even when positive residual shaping is weak.

Theory hook:
- if every trajectory entering a pocket must cross a separator `Γ` with `∫_Γ b ds >= δ`, then the pocket accumulates a minimum heuristic surcharge `λδ`;
- choosing `λ` above the typical false-attraction margin yields a sufficient condition for budget-limited search to prefer the correct corridor.

### CX2-D — `RS-PIF` (RS Passage Integral Field)

Type: `needs new base-model module`

Core idea:
1. learn a nonnegative **corridor-capacity density** `c(x, y)` and optional dead-end risk density `d(x, y)`;
2. define a secondary path functional on top of `RS` length:
   `J(π) = L_RS(π) + β ∫_π d(s) ds - γ ∫_π c(s) ds`;
3. compute or approximate the induced value field and use it as a nonlocal correction to the base heuristic.

Why this is not a copy:
- unlike `CX-B`, it is not a local bottleneck multiplier;
- unlike classical clearance heuristics, it optimizes a **path-integral quantity** tied to accessible free space over the whole route.

Why it may help:
- narrow-passage success often depends on selecting a corridor with slightly longer nominal length but much larger usable free space;
- a cumulative path-capacity field can express this trade-off, while local residual shaping cannot.

Theory hook:
- this yields a lexicographic or Pareto-style route criterion between `RS` length and integrated corridor support;
- if two corridors have close `L_RS` but one has larger integrated capacity, the resulting field systematically favors the more robust corridor under fixed budget.

## 5. Shared protocol for all `CX2-*` candidates

To avoid repeating the mistakes of `CX-A/B/C/D`, every `CX2-*` candidate should obey the following frozen rules:

1. **Public-first validation**  
   First run on `parasol_narrow` public bundle plus `mp/csm`; only push to `rs_root_hard_v2/test` after the public bundle shows a clear win.

2. **Same-alpha ablation is mandatory**  
   Compare:
   - `Hybrid A* (RS)` / `RS-only`
   - frozen `Full`
   - `Plain-Residual (same α)`
   - `CX2-*`

3. **Search-aware selection only on dev/train**  
   Candidate selection should rank by hard-family success / expansions / time deltas, never by test performance.

4. **No protocol drift**  
   No leakage, no alternative test tuning, no hidden budget changes, and no inconsistent runtime accounting.

## 6. Recommended execution order

Recommended order for the next round:
1. `CX2-A / RS-MDE`
2. `CX2-B / RS-HBF`
3. `CX2-C / RS-BCE`
4. `CX2-D / RS-PIF`

Rationale:
- `CX2-A` is the cleanest geometry-level extension of the current `RS` root line;
- `CX2-B` is the next most elegant field-level structural correction if geometry deformation alone is insufficient;
- `CX2-C` is the most direct attack on dead-end / false-attraction failure modes;
- `CX2-D` is the richest but also most coupled nonlocal formulation, so it should come after the simpler geometry/topology routes.

## 7. Bottom-line recommendation

The next successful `P0-CX` candidate is unlikely to come from another residual scaling trick.
It most likely needs to be a **geometry- or topology-structured field module** that can be argued as a
standalone method.

Among the frozen `CX2-*` candidates, the current recommendation is:
- **primary bet**: `CX2-A / RS-MDE`
- **most novel field-level follow-up**: `CX2-B / RS-HBF`
- **hard-scene safety net if dead-end behavior dominates**: `CX2-C / RS-BCE`

