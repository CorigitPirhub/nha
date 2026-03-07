# RS Field Root Protocol V1

Status: `frozen-root-protocol`  
Date: `2026-03-07`

This document freezes the **single fair protocol bundle** that is allowed to support the root claim about the `RS cost field` innovation itself.

It exists to prevent future writing from mixing:
- hard-bundle necessity evidence,
- fair nearest-baseline evidence,
- auxiliary ordinary-scene support,
- and non-fair or outdated comparison settings.

---

## 1. Scope

This protocol is only for the **root RS-field claim**.
It is **not** the protocol for the later router / weighted-search / Step 14 method line.

Use this file when the question is:
- what exactly can be claimed about the `RS cost field` itself,
- under which frozen evidence bundle,
- against which nearest baseline,
- and which statements are no longer allowed.

---

## 2. Frozen evidence blocks

### Block A — Hard-bundle necessity
Source artifacts:
- `outputs/paper/manual_v11b_exp3_full/exp_results_summary.csv`
- `outputs/paper/exp3_final_manual_v11b_manifest.json`
- `data/benchmark/parasol_narrow/meta.json`
- expanded hard-benchmark audit: `reports/rs_root_hard_benchmark_v1.md`
- expanded hard-benchmark manifest: `outputs/rs_root_hard_benchmark_v1/manifest.json`
- standardized v2 benchmark root: `data/benchmark/rs_root_hard_v2/`
- benchmark card: `docs/rs_root_hard_benchmark_card_v1.md`
- quality audit: `reports/rs_root_hard_benchmark_v2_quality.md`
- anchor-only table: `paper/tables_rs_root_v1/table_rs_root_anchor_only_comparison.csv`
- first P0-C axis-search attempt: `reports/rs_root_p0c_axis_v1.md`
- second P0-C fixed-axis verification: `reports/rs_root_p0c_axis_round2_v1.md`
- round2 paper table: `paper/tables_rs_root_v1/table_rs_root_p0c_round2_fixed_axis.csv`
- third P0-C expansion-focused search: `reports/rs_root_p0c_axis_round3_v1.md`
- round3 paper table: `paper/tables_rs_root_v1/table_rs_root_p0c_round3_expansion_focus.csv`
- fourth P0-C success-under-budget verification: `reports/rs_root_p0c_axis_round4_v1.md`
- round4 paper table: `paper/tables_rs_root_v1/table_rs_root_p0c_round4_success_budget_focus.csv`
- dedicated smoke audit on the expanded benchmark: `reports/rs_root_hard_v1_exp3_smoke.md`

Role:
- supports the claim that the `RS cost field` is a **necessary and decisive heuristic substrate** on the current hard bundle.

What this block is allowed to support:
- removing `RS` causes a large solvability collapse on `parasol_narrow/test`;
- the root value of `RS` is not cosmetic but structural;
- future RS-root hard-scene reporting should use the expanded `data/benchmark/rs_root_hard_v1/` benchmark rather than relying only on the original 18-sample bundle.

### Block B — Fair nearest-baseline comparison
Source artifact:
- `outputs/paper/manual_v11b_exp4_fair/exp_results_summary.csv`

Frozen fairness semantics:
- `hybrid_budget_cap = 0`
- `sampling_max_iters = 300`

Role:
- supports the **primary nearest-baseline** root claim.

Primary nearest baseline:
- `Hybrid A* (RS)`

Auxiliary baselines only:
- `Kinodynamic BIT*`
- `Kinodynamic RRT*`

What this block is allowed to support:
- under the frozen fair comparison, the current RS-guided model improves search effort / time over `Hybrid A* (RS)` while matching success.

What it is not allowed to support:
- a main claim that the method is generically faster than `BIT* / RRT*`, because those comparisons depend strongly on sampling-budget semantics.

### Block C — Ordinary-scene support
Source artifact:
- `outputs/paper/manual_v11b_exp12/exp_results_summary.csv`

Role:
- **auxiliary support only**.

What this block may support:
- on ordinary `mp/csm` scenes, expansions remain close to `A*`.

What this block may not support:
- a primary root-SOTA claim,
- or a claim that the method is generally time-superior on ordinary scenes.

---

## 3. Primary root claim allowed under this protocol

The strongest currently allowed root claim is:

> The `RS cost field` is the decisive heuristic substrate for solving the current hard `parasol_narrow` bundle, and under the frozen fair nearest-baseline comparison it yields a modest but positive search-effort/time advantage over `Hybrid A* (RS)` while preserving success.

This is intentionally narrower than:
- “the RS field is already a universal SOTA planner component”, or
- “the method is already broadly superior to all nearest kinodynamic baselines”.

---

## 4. Claims that are forbidden

Do **not** use this protocol to claim:
1. that the `RS cost field` alone is already a stable overall SOTA across all nearest baselines;
2. that the primary root claim should target `Kinodynamic BIT* / RRT*` instead of `Hybrid A* (RS)`;
3. that non-fair or older `BIT* / RRT*` timing wins are the canonical root result;
4. that the complete `RS + residual + upper-layer` system gain is identical to the `RS`-only root gain;
5. that a tiny hard subset (for example only a few `narrow_passage` cases) is by itself enough to justify a stable SOTA statement.

---

## 5. Artifact chain

Authoritative artifacts for this frozen root protocol:
- protocol report: `reports/rs_root_protocol_v1.md`
- protocol manifest: `outputs/rs_root_protocol_v1/manifest.json`
- hard-bundle source: `outputs/paper/manual_v11b_exp3_full/exp_results_summary.csv`
- fair nearest-baseline source: `outputs/paper/manual_v11b_exp4_fair/exp_results_summary.csv`
- ordinary-scene support source: `outputs/paper/manual_v11b_exp12/exp_results_summary.csv`

---

## P0-C Current Status

After three protocol-clean P0-C attempts, the current evidence still does **not** establish a hard nearest-baseline advantage axis against `Hybrid A* (RS)`.

Current practical reading:
- the expansion axis on high-constraint families is **not** yet established;
- the public-anchor-only subset still rejects a strong expansion-side claim;
- therefore P0-C remains open, and later work should not write the RS-root line as if this nearest-baseline axis were already solved.

## 6. Relationship to later tasks

This protocol is the required front-door filter for all later method work:
- if the root RS-field claim is not strong enough under this frozen protocol, then later upper-layer innovation cannot safely inherit a strong foundational narrative;
- therefore `TASK.md` places `P0-A` before all later steps.
