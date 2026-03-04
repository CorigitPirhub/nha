# Router Phase21 NeurIPS/ICML Positioning V1 Report

## Summary
- Goal: reframe the dual-path router as a **method** (risk-bounded adaptive computation) with a minimal, reusable core API, without changing the underlying system logic.
- Minimal demo output: `outputs/router_phase21_neurips_positioning_v1/stats.json`
- Method framing doc: `docs/neurips_method_v1.md`
- Core API: `utils/router_method_core.py`

## Contribution Triple (for abstract/introduction)
1. **Algorithm:** C2D-RBAC — a counterfactual-to-deployment framework for risk-bounded adaptive computation routing, with a static conformal+cost stage and an optional monotone-safe probe flip stage.
2. **Theory:** (i) monotone-safety of probe escalation (fast→slow only), (ii) one-sided split conformal upper prediction for conservative risk proxies, plus a Lagrangian justification for the risk-per-compute score thresholding.
3. **Empirical:** a minimal runnable demo that produces a counterfactual table, fits the core method, and demonstrates risk/compute tradeoffs under a frozen risk event definition.

Related-work alignment note:
- Phase22 implements CDT/CRC-style direct baselines and shows the static conformal stage is closely aligned; paper claims should therefore emphasize the C2D pipeline + monotone-safe probing + deployment alignment (see `paper/related_work_neurips_alignment.md`).

## Gate Check (Step 6)
- `contribution_triple_clear`: `True`
- `core_method_minimal_demo_runs`: `True` (demo runs in <10s on CPU; see `runtime_seconds` in `stats.json`)
- `api_frozen_for_baselines`: `True` (shared `fit/route`-style API via `utils/router_method_core.py`)

## Demo Snapshot (Toy)
See `outputs/router_phase21_neurips_positioning_v1/stats.json` for full details.

Key trends:
- `forced_fast` violates risk heavily.
- `conformal_stage` reduces violation probability below the target budget.
- `probe_flip_stage` further improves `J` without increasing violation probability (monotone safety).

## Artifacts
- Doc: `docs/neurips_method_v1.md`
- Core API: `utils/router_method_core.py`
- Minimal demo runner: `scripts/run_router_phase21_minimal_demo.py`
- Output: `outputs/router_phase21_neurips_positioning_v1/stats.json`
