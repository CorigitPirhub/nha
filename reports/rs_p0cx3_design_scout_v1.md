# P0-CX3 Design Scout V1

Status: `research-complete / candidate-frozen`
Date: `2026-03-08`

This note documents the **third-round design scouting** for `P0-CX`, now explicitly focused on
**avoiding `parasol_misc` regression** while still creating a hard-scene advantage axis.

Implementation follow-up for the frozen `CX3-*` family is now recorded in `reports/rs_p0cx3_round1_summary.md`. Note that the accepted summary there is the corrected post-bug-fix evidence.

Round-1 negative evidence:
- `reports/rs_p0cx_round1_summary.md`
- `outputs/rs_p0cx_round1_summary/summary.csv`

Round-2 negative evidence:
- `reports/rs_p0cx2_round1_summary.md`
- `outputs/rs_p0cx2_round1_summary/summary.csv`

## 1. Updated diagnosis after `CX2-A/B/C/D`

The new failure pattern is more specific than before:
1. `CX2-A` and `CX2-C` can produce **local improvements** on hard families such as `flange` and partially `narrow_passage`;
2. however, they also introduce **large regressions on `parasol_misc`**, which dominates the public average;
3. `CX2-B` preserves success better, but its structural bridge signal is too diffuse and still loses to same-`alpha` `Plain-Residual` on expansions;
4. `CX2-D` is clearly too aggressive and should be treated as a strong negative result.

Therefore the next round should not simply seek “more structural signal”.
It should seek **structural signal with explicit abstention, locality, and subgroup no-regression control**.

The new target is not merely:
- “improve hard families”,

but rather:
- “improve hard families **without paying for it on `parasol_misc`**”.

This makes `parasol_misc` a de facto **protected subgroup / protected regime** in the next design round.

## 2. Primary-source literature clusters consulted

Only primary sources are listed below.

### 2.1 Selective prediction / abstention / risk-controlled editing

1. `SelectiveNet: A Deep Neural Network with an Integrated Reject Option` — ICML 2019  
   https://proceedings.mlr.press/v97/geifman19a.html  
   Key takeaway: rejection should be trained jointly with prediction, not bolted on after the fact.

2. `Deep Gamblers: Learning to Abstain with Portfolio Theory` — NeurIPS 2019  
   https://papers.nips.cc/paper/9247-deep-gamblers-learning-to-abstain-with-portfolio-theory  
   Key takeaway: abstention can be implemented as an explicit optimization objective rather than an ad hoc threshold.

3. `Selective Regression under Fairness Criteria` — ICML 2022  
   https://proceedings.mlr.press/v162/shah22a.html  
   Key takeaway: a reject option can improve average performance while **hurting a subgroup**; subgroup no-regression constraints are therefore necessary.

4. `Conformal Risk Control` — 2023  
   https://people.csail.mit.edu/tals/publication/conformal_risk/  
   Key takeaway: thresholds can be calibrated to control expected risk of a monotone loss; this is attractive for bounding open-scene regression.

### 2.2 Region partition / localized specialization / graph-aware planning

5. `Learning Space Partitions for Path Planning (LaP3)` — NeurIPS 2021  
   https://papers.nips.cc/paper/2021/hash/03a3655fff3e9bdea48de9f49e938e32-Abstract.html  
   Key takeaway: adaptively learned partitions can isolate good planning sub-regions better than uniform global shaping.

6. `GraphMP: Graph Neural Network-based Motion Planning with Efficient Graph Search` — NeurIPS 2023  
   https://papers.nips.cc/paper_files/paper/2023/hash/096961cae3c3423c44ea045aeb584e05-Abstract-Conference.html  
   Key takeaway: search gains often come from coupling structural extraction with search processing, rather than only learning a single global scalar field.

### 2.3 Topology / separator / passage structure

7. `Learning Proofs of Motion Planning Infeasibility` — RSS 2021  
   https://www.roboticsproceedings.org/rss17/p064.html  
   Key takeaway: separating manifolds / obstacle-region certificates give a principled notion of where search should not go.

8. `Identification and Representation of Homotopy Classes of Trajectories for Search-based Path Planning in 3D` — RSS 2011  
   https://www.roboticsproceedings.org/rss07/p02.html  
   Key takeaway: line integrals over designed vector fields can encode topological class information useful to search.

9. `Hierarchical Motion Planning in Topological Representations` — RSS 2012  
   https://www.roboticsproceedings.org/rss08/p59.html  
   Key takeaway: difficult planning problems may require switching to or constraining via a representation with different topology.

10. `Homotopic Path Set Planning for Robot Manipulation and Navigation` — RSS 2024  
    https://www.roboticsproceedings.org/rss20/p039.html  
    Key takeaway: path length should be balanced with passage accommodation / accessible free space, and multi-path structure can help characterize that trade-off.

## 3. New design constraints distilled for `P0-CX3`

Compared with `CX2-*`, the next round must obey five stronger constraints:

1. **Protected-subgroup no-regression**  
   Treat `parasol_misc` as a protected regime. A candidate is not acceptable if it improves `flange` or `narrow_passage` but significantly worsens `parasol_misc`.

2. **Abstain-by-default editing**  
   The default behavior outside strongly justified hard regions should be exact fallback to `RS` or `Plain-Residual`, not weakly shrunk structural editing.

3. **Sparse support, not global spillover**  
   Any field perturbation should have explicitly bounded support or bounded active mass.

4. **Agreement before intervention**  
   Structural edits should only fire when multiple independent signals agree, or when a calibrated abstention module certifies low open-scene risk.

5. **Public-bundle-first with subgroup reporting**  
   Before any expanded benchmark, every candidate must report:
   - overall public `exp3/exp4`;
   - `parasol_misc` subgroup deltas;
   - hard-family subgroup deltas;
   - same-`alpha` ablation.

## 4. Frozen `P0-CX3` candidates

All candidates still preserve the same chain:

`occupancy + start/goal -> RS analytical field -> CX3 module -> fused heuristic field -> same planner`

None of them changes the task into router / planner selection.

### CX3-A — `RS-SAFE` (Selective Activation Field Editor)

Type: `needs new base-model module`

Core idea:
1. learn two objects jointly:
   - a proposed structural edit field `Δh(x, y[, θ])`;
   - an abstention / coverage field `κ(x, y[, θ]) in [0, 1]`;
2. the final edit is `κ ⊙ Δh`, while uncovered states use exact fallback to `RS` or same-`alpha` `Plain-Residual`;
3. calibrate the scene-level or region-level activation threshold using a risk-control objective so that the expected `parasol_misc` degradation stays below a chosen tolerance;
4. optionally add a protected-subgroup penalty that explicitly discourages high coverage on misc-like layouts unless the predicted benefit is strong.

Why this directly addresses the current failure:
- the main issue is not lack of structural ideas but **over-activation on misc scenes**;
- this candidate makes “whether to intervene” a first-class learned object.

Why this is not a copy:
- unlike SelectiveNet / Deep Gamblers, the reject option is not attached to a classifier output;
- it is attached to a **field edit support mask** inside a classical planner.

Theory hook:
- risk-coverage calibration can enforce `E[L_misc | activated] <= ε` for a monotone regression loss surrogate;
- bounded activation mass `||κ||_1 <= B` yields a direct upper bound on total perturbation support;
- outside the activated support, the field is exactly the frozen base, so misc regression can be explicitly limited.

### CX3-B — `RS-PSF` (Partitioned Specialist Field)

Type: `needs new base-model module`

Core idea:
1. learn a latent partition of the free space into a small number of regions:
   - inert / ordinary regions;
   - corridor-specialist regions;
   - separator-specialist regions;
2. assign a small specialist field editor to each active region type, while inert regions receive no edit at all;
3. region selection is sparse and scene-dependent, with a hard prior that open / misc scenes should mostly map to inert regions;
4. the planner still receives one fused heuristic field, but the edit is now **piecewise-structured** rather than globally applied.

Why this helps:
- `CX2-*` failed partly because global structural corrections leaked into `parasol_misc`;
- partitioned specialization localizes edits and limits spillover.

Why this is not a copy:
- unlike LaP3, this is not a planner that partitions the search space for exploration;
- it partitions the map into **field-edit regions** while keeping the current planner intact.

Theory hook:
- if the total area of non-inert partitions is bounded and misc scenes activate mostly inert regions, then expected misc perturbation is bounded;
- specialist fields can be analyzed as local perturbations on subdomains, making the no-regression story cleaner.

### CX3-C — `RS-CCP` (Consensus-Certified Perturbation)

Type: `needs new base-model module`

Core idea:
1. maintain several independent structural witnesses, e.g. morphology, barrier, bridge, passage-capacity;
2. convert each witness into a signed local edit proposal;
3. only apply a nonzero perturbation where:
   - a sufficient number of witnesses agree on sign and support, and
   - their disagreement score is below a threshold;
4. elsewhere, hard fallback to base.

Why this helps:
- `parasol_misc` degradation strongly suggests that a single structural witness is too brittle;
- open scenes often produce weak or contradictory structure cues, which should trigger abstention.

Why this is not a copy:
- this is not expert routing across planners;
- it is **consensus filtering over field perturbations** before a single heuristic field is emitted.

Theory hook:
- if the perturbation is zero whenever witness variance exceeds `τ`, then false interventions in ambiguous regions are controlled by the disagreement rate;
- agreement-based support can be interpreted as a higher-confidence subset of edits, analogous to selective prediction but at field level.

### CX3-D — `RS-HPG` (Homotopy-Preserving Guard)

Type: `needs new base-model module`

Core idea:
1. construct a lightweight topological guard signal from obstacle skeletons / separators / reference loops;
2. for any proposed structural edit, measure whether it would change the open-scene route preference in a way inconsistent with the base `RS` topology;
3. veto edits that alter the topological signature on easy / misc scenes, while allowing edits that only sharpen already-necessary bottleneck preferences on hard scenes;
4. effectively, this is a **topology-preserving edit filter** on top of any structural field proposal.

Why this helps:
- `parasol_misc` regressions are often caused by overcommitting to a nonessential structure;
- a topological guard can suppress edits that unnecessarily change route bias in easy scenes.

Why this is not a copy:
- unlike classical homotopy-constrained planning, it does not enumerate classes or replace the planner;
- it uses topological signatures only as a **veto mechanism for heuristic editing**.

Theory hook:
- if the edit preserves the reference homotopy integral up to tolerance `τ` on open-scene loops, then the easy-scene ordering induced by the base field is approximately preserved;
- edits are therefore allowed only when they are topologically conservative where conservatism matters most.

## 5. Shared execution rules for `CX3-*`

Every `CX3-*` candidate must satisfy all of the following before any expanded benchmark run:

1. **Public-first validation**  
   First run only on `parasol_narrow` public bundle plus `mp/csm`.

2. **Protected-subgroup report is mandatory**  
   Report `parasol_misc`, `narrow_passage`, `flange`, `maze`, and overall averages.

3. **Protected-subgroup stop rule**  
   If `parasol_misc` success drops or if `parasol_misc` expansions worsen materially against same-`alpha` `Plain-Residual`, stop early.

4. **Same-alpha ablation is mandatory**  
   Compare:
   - `Hybrid A* (RS)` / `RS-only`
   - frozen `Full`
   - `Plain-Residual (same α)`
   - `CX3-*`

5. **No protocol drift**  
   No tuning on test, no hidden budget changes, no leakage, and no inconsistent runtime accounting.

## 6. Recommended execution order

Recommended order for the next round:
1. `CX3-A / RS-SAFE`
2. `CX3-B / RS-PSF`
3. `CX3-C / RS-CCP`
4. `CX3-D / RS-HPG`

Rationale:
- `CX3-A` directly attacks the newly identified root problem: unprotected activation on `parasol_misc`;
- `CX3-B` is the next most natural if explicit abstention alone is not enough and localization is the main issue;
- `CX3-C` comes next when multiple brittle structure signals need consensus filtering;
- `CX3-D` is the most elegant topological veto, but also the most theory-heavy and implementation-sensitive.

## 7. Bottom-line recommendation

The most promising `P0-CX3` direction is not “more structure”, but **structure with explicit abstention and protected-subgroup guarantees**.

Current recommendation:
- **primary bet**: `CX3-A / RS-SAFE`
- **best locality-based follow-up**: `CX3-B / RS-PSF`
- **best robustness-based follow-up**: `CX3-C / RS-CCP`
- **highest-risk / highest-concept option**: `CX3-D / RS-HPG`
